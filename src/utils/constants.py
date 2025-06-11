from enum import Enum

class CallbackData(Enum):
    ADD_PORTFOLIO = "add_portfolio"
    ADD_TICKER = "add_ticker"
    REMOVE_TICKER = "remove_ticker"
    BACK = "back"
    NAME = "name"
    URL = "url"
    THRESHOLD = "threshold"
    TICKER_NAME = "ticker_name"

class UserDataKeys(Enum):
    CURRENT_FIELD = "current_field"
    PORTFOLIO_NAME = "portfolio_name"
    PORTFOLIO_URL = "portfolio_url"
    PORTFOLIO_THRESHOLD = "portfolio_threshold"
