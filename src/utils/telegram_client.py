import requests
import logging
from config.settings import config

logger = logging.getLogger(__name__)

class TelegramClient:
    @staticmethod
    def send_message(message: str, parse_mode: str = 'HTML', disable_preview: bool = True) -> bool:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': config.CHAT_ID,
            'text': message,
            'parse_mode': parse_mode,
            "disable_web_page_preview": disable_preview
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
