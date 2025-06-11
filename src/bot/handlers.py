import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from src.bot.keyboards import KeyboardFactory
from src.utils.constants import CallbackData, UserDataKeys
from src.utils.data_manager import DataManager
from src.utils.decorators import handle_exceptions
from config.settings import config

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        self.data_manager = DataManager()
        self.keyboards = KeyboardFactory()

    @handle_exceptions
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Welcome! Use /commands to access the menu.")

    @handle_exceptions
    async def commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        reply_markup = self.keyboards.main_menu()
        await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

    @handle_exceptions
    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()

        if query.data == CallbackData.ADD_PORTFOLIO.value:
            reply_markup = self.keyboards.portfolio_fields()
            await query.edit_message_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

        elif query.data == CallbackData.ADD_TICKER.value:
            await query.edit_message_text("Please enter the name of the ticker to add:")
            context.user_data[UserDataKeys.CURRENT_FIELD.value] = CallbackData.TICKER_NAME.value

        elif query.data == CallbackData.REMOVE_TICKER.value:
            tickers = self.data_manager.load_tickers()
            keyboard = [
                [self.keyboards.create_button(ticker, f"remove_{ticker}")] for ticker in tickers
            ]
            keyboard.append([self.keyboards.create_button("Back", CallbackData.BACK.value)])
            reply_markup = self.keyboards.create_markup(keyboard)
            await query.edit_message_text("Select a ticker to remove:", reply_markup=reply_markup)

        elif query.data.startswith("remove_"):
            await self._handle_ticker_removal(query)

        elif query.data == CallbackData.NAME.value:
            await query.edit_message_text("Please enter the portfolio name:")
            context.user_data[UserDataKeys.CURRENT_FIELD.value] = CallbackData.NAME.value

        elif query.data == CallbackData.URL.value:
            await query.edit_message_text("Please enter the portfolio URL:")
            context.user_data[UserDataKeys.CURRENT_FIELD.value] = CallbackData.URL.value

        elif query.data == CallbackData.THRESHOLD.value:
            await query.edit_message_text("Please enter the portfolio threshold:")
            context.user_data[UserDataKeys.CURRENT_FIELD.value] = CallbackData.THRESHOLD.value

        elif query.data == CallbackData.BACK.value:
            reply_markup = self.keyboards.main_menu()
            await query.edit_message_text("Choose an option:", reply_markup=reply_markup)

    async def _handle_ticker_removal(self, query):
        ticker_to_remove = query.data.split("_")[1]
        portfolios = self.data_manager.load_portfolios()
        tickers = self.data_manager.load_tickers()
        
        if ticker_to_remove in tickers:
            tickers.remove(ticker_to_remove)
            self.data_manager.save_data(portfolios, tickers)
            await query.edit_message_text(f"Ticker '{ticker_to_remove}' removed successfully!")
        else:
            await query.edit_message_text(f"Ticker '{ticker_to_remove}' not found.")

    @handle_exceptions
    async def handle_user_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        portfolios = self.data_manager.load_portfolios()
        tickers = self.data_manager.load_tickers()
        
        current_field = context.user_data.get(UserDataKeys.CURRENT_FIELD.value)

        if current_field == CallbackData.NAME.value:
            await self._handle_name_input(update, context)
        elif current_field == CallbackData.URL.value:
            await self._handle_url_input(update, context)
        elif current_field == CallbackData.THRESHOLD.value:
            await self._handle_threshold_input(update, context, portfolios, tickers)
        elif current_field == CallbackData.TICKER_NAME.value:
            await self._handle_ticker_input(update, portfolios, tickers)

    async def _handle_name_input(self, update, context):
        context.user_data[UserDataKeys.PORTFOLIO_NAME.value] = update.message.text
        await update.message.reply_text(f"Portfolio name set to: {update.message.text}")
        
        reply_markup = self.keyboards.portfolio_fields()
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    async def _handle_url_input(self, update, context):
        context.user_data[UserDataKeys.PORTFOLIO_URL.value] = update.message.text
        await update.message.reply_text(f"Portfolio URL set to: {update.message.text}")
        
        reply_markup = self.keyboards.portfolio_fields()
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    async def _handle_threshold_input(self, update, context, portfolios, tickers):
        try:
            threshold_value = float(update.message.text)
            context.user_data[UserDataKeys.PORTFOLIO_THRESHOLD.value] = threshold_value
            await update.message.reply_text(f"Portfolio threshold set to: {threshold_value}")

            if self._all_portfolio_fields_set(context.user_data):
                await self._create_portfolio(update, context, portfolios, tickers)

        except ValueError:
            await update.message.reply_text("Invalid threshold value. Please enter a number.")

        reply_markup = self.keyboards.portfolio_fields()
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    async def _handle_ticker_input(self, update, portfolios, tickers):
        ticker_name = update.message.text.upper()

        if ticker_name not in tickers:
            tickers.append(ticker_name)
            self.data_manager.save_data(portfolios, tickers)
            await update.message.reply_text(f"Ticker '{ticker_name}' added successfully!")
        else:
            await update.message.reply_text(f"Ticker '{ticker_name}' already exists.")

    def _all_portfolio_fields_set(self, user_data):
        required_fields = [
            UserDataKeys.PORTFOLIO_NAME.value,
            UserDataKeys.PORTFOLIO_URL.value,
            UserDataKeys.PORTFOLIO_THRESHOLD.value
        ]
        return all(field in user_data for field in required_fields)

    async def _create_portfolio(self, update, context, portfolios, tickers):
        new_portfolio = {
            "name": context.user_data.get(UserDataKeys.PORTFOLIO_NAME.value),
            "url": context.user_data.get(UserDataKeys.PORTFOLIO_URL.value),
            "threshold": context.user_data.get(UserDataKeys.PORTFOLIO_THRESHOLD.value),
            "totalLostOrGainedSinceTheStartOfTheScript": 0,
        }
        portfolios.append(new_portfolio)
        self.data_manager.save_data(portfolios, tickers)
        await update.message.reply_text(f"Portfolio '{new_portfolio['name']}' added successfully!")

def setup_bot():
    handlers = BotHandlers()
    
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("commands", handlers.commands))
    application.add_handler(CallbackQueryHandler(handlers.handle_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_user_input))

    application.run_polling()
