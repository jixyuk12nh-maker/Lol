import discord
from discord import app_commands
import re
from typing import Dict

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class EmojiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.emoji_cache = {}  # 서버별 이모지 캐시

    async def setup_hook(self):
        await self.tree.sync()
        print("봇이 시작되었습니다!")

    async def get_server_emojis(self, guild: discord.Guild) -> Dict[str, str]:
        """서버의 커스텀 이모지를 딕셔너리로 반환"""
        if guild.id in self.emoji_cache:
            return self.emoji_cache[guild.id]
        
        emoji_dict = {}
        for emoji in guild.emojis:
            if emoji.animated:
                emoji_dict[emoji.name] = f"<a:{emoji.name}:{emoji.id}>"
            else:
                emoji_dict[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
        
        self.emoji_cache[guild.id] = emoji_dict
        return emoji_dict

    def replace_emoji_names(self, text: str, guild: discord.Guild) -> str:
        """:이모지이름: 형식을 실제 이모지로 변환"""
        if not text or not guild:
            return text
        
        emoji_dict = self.emoji_cache.get(guild.id, {})
        
        def replace(match):
            name = match.group(1)
            return emoji_dict.get(name, match.group(0))
        
        return re.sub(r':([a-zA-Z0-9_]+):', replace, text)

bot = EmojiBot()

@bot.tree.command(name="임베드", description="서버 커스텀 이모지를 지원하는 Embed 생성")
@app_commands.describe(
    제목="Embed 제목",
    설명="Embed 설명",
    푸터="Embed 푸터"
)
async def embed_command(
    interaction: discord.Interaction,
    제목: str = None,
    설명: str = None,
    푸터: str = None
):
    """서버 커스텀 이모지를 지원하는 Embed 명령어"""
    
    # 서버 이모지 캐시 업데이트
    if interaction.guild:
        await bot.get_server_emojis(interaction.guild)
    
    # Embed 생성
    embed = discord.Embed(color=0x00ff00)
    
    # 제목 변환 및 설정
    if 제목:
        embed.title = bot.replace_emoji_names(제목, interaction.guild)
    
    # 설명 변환 및 설정
    if 설명:
        embed.description = bot.replace_emoji_names(설명, interaction.guild)
    
    # 푸터 변환 및 설정
    if 푸터:
        embed.set_footer(text=bot.replace_emoji_names(푸터, interaction.guild))
    
    # 최소한 하나의 필드가 있어야 함
    if not (제목 or 설명 or 푸터):
        embed.description = "서버 커스텀 이모지를 사용해보세요! 😊"
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"{bot.user}가 연결되었습니다!")
    print(f"서버 수: {len(bot.guilds)}")
    
    # 모든 서버의 이모지 캐시 초기화
    for guild in bot.guilds:
        await bot.get_server_emojis(guild)

@bot.event
async def on_guild_join(guild):
    """새 서버에 입장했을 때"""
    await bot.get_server_emojis(guild)
    print(f"{guild.name} 서버에 입장했습니다!")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    """서버 이모지가 변경되었을 때 캐시 갱신"""
    bot.emoji_cache[guild.id] = {}
    await bot.get_server_emojis(guild)

# 봇 실행
bot.run('YOUR_BOT_TOKEN_HERE')
