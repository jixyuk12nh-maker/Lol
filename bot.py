import os
import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

async def update_info_channels(guild):
    """채널 이름으로 서버 정보 표시"""
    
    # 멤버 수 계산
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    
    # 채널 이름 생성
    humans_name = f"・Humans: {humans}"
    bots_name = f"・Bots: {bots}"
    members_name = f"・Members: {total}"
    
    # 채널 생성 또는 업데이트
    await create_or_update_channel(guild, humans_name)
    await create_or_update_channel(guild, bots_name)
    await create_or_update_channel(guild, members_name)

async def create_or_update_channel(guild, name):
    """채널 생성 또는 이름 업데이트"""
    
    # 채널 이름이 100자 이하인지 확인
    if len(name) > 100:
        name = name[:97] + "..."
    
    # 기존 채널 찾기
    for channel in guild.channels:
        if channel.name == name and isinstance(channel, discord.VoiceChannel):
            return channel
    
    # 같은 종류의 채널이 있는지 확인 (Humans, Bots, Members 중 하나)
    for channel in guild.channels:
        if isinstance(channel, discord.VoiceChannel):
            if "Humans" in channel.name and "Humans" in name:
                await channel.edit(name=name)
                return channel
            elif "Bots" in channel.name and "Bots" in name:
                await channel.edit(name=name)
                return channel
            elif "Members" in channel.name and "Members" in name:
                await channel.edit(name=name)
                return channel
    
    # 새 음성 채널 생성
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            connect=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            connect=True
        )
    }
    
    channel = await guild.create_voice_channel(
        name,
        overwrites=overwrites,
        reason="서버 정보 채널 생성"
    )
    
    return channel

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 실행됨")
    await tree.sync()
    print("✅ 명령어 동기화 완료")
    
    # 모든 서버에 채널 생성 및 업데이트
    for guild in bot.guilds:
        await update_info_channels(guild)
        print(f"✅ {guild.name} 서버 정보 채널 준비 완료")

@bot.event
async def on_member_join(member):
    """새 멤버 입장"""
    await update_info_channels(member.guild)

@bot.event
async def on_member_remove(member):
    """멤버 퇴장"""
    await update_info_channels(member.guild)

@tree.command(name="정보채널", description="서버 정보 채널을 생성/업데이트합니다")
async def info_channel(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 처리 중...", ephemeral=True)
    
    await update_info_channels(interaction.guild)
    
    await interaction.edit_original_response(
        content=f"✅ 정보 채널이 업데이트되었습니다!"
    )

# 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)
    
    bot.run(token)
