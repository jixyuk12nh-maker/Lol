import os
import discord
from discord import app_commands
import re

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========== 서버 정보 채널 관련 함수 ==========

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

# ========== 임베드 명령어 ==========

@tree.command(name="임베드", description="Embed 메시지를 생성합니다")
@app_commands.describe(
    내용="표시할 내용",
    제목="Embed 제목 (선택)",
    색상="색상 코드 (예: #FF0000, #00FF00) (선택)",
    이미지="이미지 URL (선택)",
    썸네일="썸네일 URL (선택)"
)
async def embed_command(
    interaction: discord.Interaction,
    내용: str,
    제목: str = None,
    색상: str = None,
    이미지: str = None,
    썸네일: str = None
):
    """Embed 메시지 생성"""
    
    # 에페멀 메시지로 "전송 완료" 표시 (나만 보임)
    await interaction.response.send_message("✅ Embed가 전송되었습니다!", ephemeral=True)
    
    # Embed 생성
    embed = discord.Embed(description=내용)
    
    # 제목 설정
    if 제목:
        embed.title = 제목
    
    # 색상 설정
    if 색상:
        try:
            color_hex = 색상.lstrip('#')
            embed.color = int(color_hex, 16)
        except ValueError:
            embed.color = 0x00ff00
    else:
        embed.color = 0x00ff00
    
    # 이미지 설정
    if 이미지:
        embed.set_image(url=이미지)
    
    # 썸네일 설정
    if 썸네일:
        embed.set_thumbnail(url=썸네일)
    
    # 타임스탬프 추가
    embed.timestamp = discord.utils.utcnow()
    
    # 현재 채널에 Embed 전송
    await interaction.channel.send(embed=embed)

# ========== 서버 정보 채널 명령어 ==========

@tree.command(name="정보채널", description="서버 정보 채널을 생성/업데이트합니다")
async def info_channel(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 처리 중...", ephemeral=True)
    
    await update_info_channels(interaction.guild)
    
    await interaction.edit_original_response(
        content="✅ 정보 채널이 업데이트되었습니다!"
    )

# ========== 핑 명령어 (봇 상태 확인) ==========

@tree.command(name="핑", description="봇의 응답 속도를 확인합니다")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 퐁! 응답 속도: {latency}ms", ephemeral=True)

# ========== 서버 정보 명령어 ==========

@tree.command(name="서버정보", description="서버의 기본 정보를 표시합니다")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    
    embed = discord.Embed(
        title=f"📊 {guild.name} 서버 정보",
        description=f"""
👤 **Humans:** {humans}
🤖 **Bots:** {bots}
👥 **Members:** {total}
📅 **생성일:** {guild.created_at.strftime('%Y년 %m월 %d일')}
👑 **서버장:** {guild.owner.mention}
📌 **채널 수:** {len(guild.channels)}
🎨 **역할 수:** {len(guild.roles)}
        """.strip(),
        color=0x00ff00,
        timestamp=discord.utils.utcnow()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

# ========== 이벤트 ==========

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 실행됨")
    await tree.sync()
    print("✅ 명령어 동기화 완료")
    
    # 모든 서버에 채널 생성 및 업데이트
    for guild in bot.guilds:
        await update_info_channels(guild)
        print(f"✅ {guild.name} 서버 정보 채널 준비 완료")
    
    print(f"📊 총 {len(bot.guilds)}개 서버 연결됨")

@bot.event
async def on_member_join(member):
    """새 멤버 입장"""
    await update_info_channels(member.guild)

@bot.event
async def on_member_remove(member):
    """멤버 퇴장"""
    await update_info_channels(member.guild)

@bot.event
async def on_guild_join(guild):
    """새 서버 입장"""
    await update_info_channels(guild)
    print(f"✅ {guild.name} 서버에 입장했고 정보 채널을 생성했습니다!")

@bot.event
async def on_error(event, *args, **kwargs):
    """에러 처리"""
    print(f"❌ 에러 발생: {event}")

# ========== 실행 ==========

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)
    
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("❌ 잘못된 토큰입니다. 환경변수를 확인해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
