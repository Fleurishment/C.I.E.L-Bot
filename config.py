import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
    DEFAULT_REGION = os.getenv('DEFAULT_REGION', 'NA')
    
    # Rate limiting
    RATE_LIMIT_PER_SECOND = 5
    
    # Embed settings
    MAX_EMBED_DESCRIPTION = 4096
    MAX_FIELD_VALUE = 1024
    
    @staticmethod
    def validate():
        if not Config.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN not found in environment variables!")
