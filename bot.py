import os
import discord
from discord import app_commands
import re

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 서버 이모지 캐시
emoji_cache = {}

def get_emojis(guild):
    """서버 이모지 가져오기"""
    if not guild:
        return {}
    
    if guild.id in emoji_cache:
        return emoji_cache[guild.id]
    
    emojis = {}
    for emoji in guild.emojis:
        if emoji.animated:
            emojis[emoji.name] = f"<a:{emoji.name}:{emoji.id}>"
        else:
            emojis[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
    
    emoji_cache[guild.id] = emojis
    return emojis

def convert_emoji(text, guild):
    """:이름: -> 실제 이모지로 변환"""
    if not text or not guild:
        return text
    
    emojis = get_emojis(guild)
    
    def replace(match):
        name = match.group(1)
        return emojis.get(name, match.group(0))
    
    return re.sub(r':([a-zA-Z0-9_]+):', replace, text)

@tree.command(name="임베드", description="이모지가 포함된 Embed 생성")
@app_commands.describe(
    내용="Embed에 표시할 내용 (이모지: :이름: 형식)"
)
async def embed_cmd(
    interaction: discord.Interaction,
    내용: str
):
    # 바로 응답
    await interaction.response.send_message("⏳ 생성 중...", ephemeral=True)
    
    try:
        # 이모지 변환
        converted_text = convert_emoji(내용, interaction.guild)
        
        # Embed 생성
        embed = discord.Embed(
            description=converted_text,
            color=0x5865F2  # Discord 블루
        )
        
        # 원본 메시지 수정
        await interaction.edit_original_response(content=None, embed=embed)
        
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ 오류: {str(e)}")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} 로그인됨")
    await tree.sync()
    
    # 캐시 초기화
    for guild in bot.guilds:
        get_emojis(guild)
    
    print(f"📊 서버 {len(bot.guilds)}개")
    print(f"🎨 총 이모지: {sum(len(guild.emojis) for guild in bot.guilds)}개")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    """이모지 변경시 캐시 갱신"""
    if guild.id in emoji_cache:
        del emoji_cache[guild.id]
    get_emojis(guild)

# 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경변수가 없습니다!")
        exit(1)
    
    bot.run(token)
