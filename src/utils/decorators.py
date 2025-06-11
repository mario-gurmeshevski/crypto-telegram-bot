import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def handle_exceptions(func):
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(self, update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            try:
                if update.message:
                    await update.message.reply_text("Sorry, an error occurred. Please try again.")
                elif update.callback_query:
                    await update.callback_query.message.reply_text("Sorry, an error occurred. Please try again.")
            except Exception as notification_error:
                logger.error(f"Failed to send error notification: {notification_error}")
    
    return wrapper
