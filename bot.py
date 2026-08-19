import os
import discord
from discord import app_commands
import re

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 서버별 이모지 캐시
emoji_cache = {}

def get_server_emojis(guild):
    """서버의 모든 커스텀 이모지를 가져옴"""
    if not guild:
        return {}
    
    if guild.id in emoji_cache:
        return emoji_cache[guild.id]
    
    emojis = {}
    for emoji in guild.emojis:
        # 이미 <:name:id> 형식으로 저장
        if emoji.animated:
            emojis[emoji.name] = f"<a:{emoji.name}:{emoji.id}>"
        else:
            emojis[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
    
    emoji_cache[guild.id] = emojis
    return emojis

def replace_emoji(text, guild):
    """
    텍스트 내의 이모지를 변환
    1. :이름: -> <:이름:ID> (서버 이모지로 변환)
    2. <:이름:ID> 형식은 그대로 유지
    3. 없는 이모지는 텍스트로 유지
    """
    if not text or not guild:
        return text
    
    emojis = get_server_emojis(guild)
    
    # 1. :이름: 형식 변환
    def replace_colon_emoji(match):
        name = match.group(1)
        # 서버에 있는 이모지만 변환
        return emojis.get(name, match.group(0))
    
    text = re.sub(r':([a-zA-Z0-9_]+):', replace_colon_emoji, text)
    
    # 2. <:이름:ID> 또는 <a:이름:ID> 형식은 그대로 유지 (검증만)
    # 이미 올바른 형식이면 그대로 둠
    return text

@tree.command(
    name="임베드",
    description="서버 커스텀 이모지를 지원하는 Embed 생성"
)
@app_commands.describe(
    제목="Embed 제목",
    설명="Embed 설명",
    푸터="Embed 푸터 텍스트",
    색상="색상 코드 (예: #FF0000, #00FF00)",
    이미지="이미지 URL",
    썸네일="썸네일 URL"
)
async def embed_command(
    interaction: discord.Interaction,
    제목: str = None,
    설명: str = None,
    푸터: str = None,
    색상: str = None,
    이미지: str = None,
    썸네일: str = None
):
    """임베드 생성 명령어"""
    
    if not interaction.guild:
        await interaction.response.send_message(
            "이 명령어는 서버에서만 사용 가능합니다.",
            ephemeral=True
        )
        return
    
    # Embed 생성
    embed = discord.Embed()
    
    # 색상 설정
    if 색상:
        try:
            color_hex = 색상.lstrip('#')
            embed.color = int(color_hex, 16)
        except ValueError:
            embed.color = 0x00ff00  # 기본값
    else:
        embed.color = 0x00ff00
    
    # 제목 설정 (이모지 변환)
    if 제목:
        embed.title = replace_emoji(제목, interaction.guild)
    
    # 설명 설정 (이모지 변환)
    if 설명:
        embed.description = replace_emoji(설명, interaction.guild)
    
    # 푸터 설정 (이모지 변환)
    if 푸터:
        embed.set_footer(text=replace_emoji(푸터, interaction.guild))
    
    # 이미지 설정
    if 이미지:
        embed.set_image(url=이미지)
    
    # 썸네일 설정
    if 썸네일:
        embed.set_thumbnail(url=썸네일)
    
    # 최소 하나의 필드 확인
    if not (제목 or 설명 or 푸터):
        embed.description = "서버 커스텀 이모지를 사용해보세요! 😊\n\n예시: :Potassium:"

    # 기본 타임스탬프 추가 (선택사항)
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 실행됨!")
    await tree.sync()
    
    # 모든 서버 이모지 캐시
    for guild in bot.guilds:
        get_server_emojis(guild)
    
    print(f"📊 서버 {len(bot.guilds)}개 연결됨")
    print(f"🎨 총 이모지 수: {sum(len(guild.emojis) for guild in bot.guilds)}개")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    """이모지 변경시 캐시 갱신"""
    if guild.id in emoji_cache:
        del emoji_cache[guild.id]
    get_server_emojis(guild)
    print(f"🔄 {guild.name} 서버 이모지 업데이트됨")

# 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 설정되지 않았습니다!")
        exit(1)
    
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("❌ 잘못된 토큰입니다. 환경변수를 확인해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
