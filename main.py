import asyncio
import logging
from threading import Thread
from src.bot.handlers import setup_bot
from src.monitoring.crypto_monitor import monitor_market_updates
from src.monitoring.portfolio_monitor import monitor_portfolios

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Crypto Portfolio & Market Monitor Bot...")
    
    try:
        market_thread = Thread(target=monitor_market_updates, daemon=True)
        market_thread.start()
        logger.info("Market monitoring thread started")
        
        portfolio_thread = Thread(target=monitor_portfolios, daemon=True)
        portfolio_thread.start()
        logger.info("Portfolio monitoring thread started")
        
        logger.info("Starting Telegram bot...")
        setup_bot()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
