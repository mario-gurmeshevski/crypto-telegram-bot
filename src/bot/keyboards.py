from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.constants import CallbackData

class KeyboardFactory:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("Add Portfolio", callback_data=CallbackData.ADD_PORTFOLIO.value)],
            [InlineKeyboardButton("Add Ticker", callback_data=CallbackData.ADD_TICKER.value)],
            [InlineKeyboardButton("Remove Ticker", callback_data=CallbackData.REMOVE_TICKER.value)],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def portfolio_fields() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("Name", callback_data=CallbackData.NAME.value)],
            [InlineKeyboardButton("URL", callback_data=CallbackData.URL.value)],
            [InlineKeyboardButton("Threshold", callback_data=CallbackData.THRESHOLD.value)],
            [InlineKeyboardButton("Back", callback_data=CallbackData.BACK.value)],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_button(text: str, callback_data: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=callback_data)
    
    @staticmethod
    def create_markup(keyboard: list) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(keyboard)
