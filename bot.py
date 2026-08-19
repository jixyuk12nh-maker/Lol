import os
import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 설정
CHANNEL_NAME = "서버-정보"

async def create_info_channel(guild):
    """서버 정보 채널 생성"""
    # 기존 채널 찾기
    for channel in guild.channels:
        if channel.name == CHANNEL_NAME and isinstance(channel, discord.TextChannel):
            return channel
    
    # 새 채널 생성
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True
        )
    }
    
    channel = await guild.create_text_channel(
        CHANNEL_NAME,
        overwrites=overwrites,
        reason="서버 정보 채널 생성"
    )
    
    return channel

async def update_info(channel):
    """정보 업데이트"""
    guild = channel.guild
    
    # 멤버 수 계산
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    
    # 텍스트로 표시 (이모지 없이)
    content = f"""
・Humans: {humans}
・Bots: {bots}
・Members: {total}
    """.strip()
    
    # 기존 메시지 찾기
    async for msg in channel.history(limit=10):
        if msg.author == bot.user and not msg.embeds:
            await msg.edit(content=content)
            return
    
    # 없으면 새로 보내기
    await channel.send(content)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 실행됨")
    await tree.sync()
    print("✅ 명령어 동기화 완료")
    
    # 모든 서버에 채널 생성 및 업데이트
    for guild in bot.guilds:
        channel = await create_info_channel(guild)
        await update_info(channel)
        print(f"✅ {guild.name} 서버 정보 채널 준비 완료")

@bot.event
async def on_member_join(member):
    """새 멤버 입장"""
    channel = discord.utils.get(member.guild.channels, name=CHANNEL_NAME)
    if channel:
        await update_info(channel)

@bot.event
async def on_member_remove(member):
    """멤버 퇴장"""
    channel = discord.utils.get(member.guild.channels, name=CHANNEL_NAME)
    if channel:
        await update_info(channel)

@tree.command(name="정보채널", description="서버 정보 채널을 생성/업데이트합니다")
async def info_channel(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 처리 중...", ephemeral=True)
    
    channel = await create_info_channel(interaction.guild)
    await update_info(channel)
    
    await interaction.edit_original_response(
        content=f"✅ 정보 채널이 준비되었습니다!\n{channel.mention}"
    )

# 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)
    
    bot.run(token)
