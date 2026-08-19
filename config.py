import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    @staticmethod
    def validate():
        if not Config.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
