import os
import discord
from discord import app_commands
import re

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 서버별 이모지 저장
emoji_cache = {}

def get_server_emojis(guild):
    """서버 이모지 가져오기"""
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

def replace_emoji(text, guild):
    """:이모지이름: -> 실제 이모지로 변환"""
    if not text or not guild:
        return text
    
    emojis = get_server_emojis(guild)
    
    def replace(match):
        name = match.group(1)
        return emojis.get(name, match.group(0))
    
    return re.sub(r':([a-zA-Z0-9_]+):', replace, text)

@tree.command(name="임베드", description="이모지 지원 Embed 생성")
@app_commands.describe(
    제목="제목 입력",
    설명="설명 입력", 
    푸터="푸터 입력"
)
async def embed(interaction, 제목: str = None, 설명: str = None, 푸터: str = None):
    if not interaction.guild:
        await interaction.response.send_message("서버에서 사용해주세요.", ephemeral=True)
        return
    
    embed = discord.Embed(color=0x00ff00)
    
    if 제목:
        embed.title = replace_emoji(제목, interaction.guild)
    if 설명:
        embed.description = replace_emoji(설명, interaction.guild)
    if 푸터:
        embed.set_footer(text=replace_emoji(푸터, interaction.guild))
    
    if not (제목 or 설명 or 푸터):
        embed.description = "이모지를 사용해보세요! :smile:"
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"{bot.user} 실행됨!")
    await tree.sync()
    
    # 모든 서버 이모지 캐시
    for guild in bot.guilds:
        get_server_emojis(guild)
    print(f"서버 {len(bot.guilds)}개 연결됨")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    """이모지 변경시 캐시 갱신"""
    if guild.id in emoji_cache:
        del emoji_cache[guild.id]
    get_server_emojis(guild)

# 실행 - 여기에 토큰 넣으세요
bot.run(os.getenv("DISCORD_TOKEN"))
