import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID: str = os.getenv("CHAT_ID")
    COINMARKETCAP_API_KEY: str = os.getenv("COINMARKETCAP_API_KEY")
    CHROME_DRIVER_PATH: str = os.getenv("CHROME_DRIVER_PATH")
    
    PORTFOLIOS_FILE: str = "data/portfolios.json"
    TICKERS_FILE: str = "data/tickers.json"
    
    CRYPTO_UPDATE_INTERVAL: int = 1800
    PORTFOLIO_UPDATE_INTERVAL: int = 600
    
    SELENIUM_TIMEOUT: int = 15
    PAGE_LOAD_DELAY: int = 5

config = Config()
