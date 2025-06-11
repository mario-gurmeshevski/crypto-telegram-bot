import time
import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from src.utils.telegram_client import TelegramClient
from src.utils.data_manager import DataManager
from config.settings import config

logger = logging.getLogger(__name__)

class CryptoMarketMonitor:
    def __init__(self):
        self.telegram_client = TelegramClient()
        self.data_manager = DataManager()
        self.previous_dominance = {"btc_dominance": None}
        self.previous_prices = {}

    def fetch_crypto_market_data(self, symbols: list) -> Optional[Dict[str, Any]]:
        try:
            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': config.COINMARKETCAP_API_KEY,
            }

            global_data = self._fetch_global_metrics(headers)
            if not global_data:
                return None

            coins_data = self._fetch_coins_data(headers)
            if not coins_data:
                return None

            return self._process_market_data(global_data, coins_data, symbols)

        except Exception as e:
            logger.error(f"Failed to fetch crypto market data: {e}")
            return None

    def _fetch_global_metrics(self, headers: dict) -> Optional[dict]:
        try:
            url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch global metrics: {e}")
            return None

    def _fetch_coins_data(self, headers: dict) -> Optional[list]:
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
            params = {"start": 1, "limit": 3500, "convert": "USD"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()["data"]
        except requests.RequestException as e:
            logger.error(f"Failed to fetch coins data: {e}")
            return None

    def _process_market_data(self, global_data: dict, coins_data: list, symbols: list) -> dict:
        valid_coins = [coin for coin in coins_data if coin["quote"]["USD"].get("percent_change_24h") is not None]
        
        top_gainer = max(valid_coins, key=lambda x: x["quote"]["USD"]["percent_change_24h"], default=None)
        top_loser = min(valid_coins, key=lambda x: x["quote"]["USD"]["percent_change_24h"], default=None)

        global_quote = global_data["data"]["quote"]["USD"]
        total_market_cap = global_quote["total_market_cap"]
        bitcoin_dominance = global_data["data"]["btc_dominance"]
        ethereum_dominance = global_data["data"]["eth_dominance"]
        altcoin_dominance = 100 - bitcoin_dominance - ethereum_dominance

        filtered_data = {}
        for symbol in symbols:
            coin_data = next((coin for coin in coins_data if coin["symbol"] == symbol), None)
            if coin_data:
                filtered_data[symbol] = {
                    "name": coin_data["name"],
                    "price": coin_data["quote"]["USD"].get("price"),
                    "change_24h": coin_data["quote"]["USD"].get("percent_change_24h"),
                }

        return {
            "filtered_data": filtered_data,
            "top_gainer": self._format_coin_data(top_gainer) if top_gainer else None,
            "top_loser": self._format_coin_data(top_loser) if top_loser else None,
            "total_market_cap": total_market_cap,
            "bitcoin_dominance": bitcoin_dominance,
            "ethereum_dominance": ethereum_dominance,
            "altcoin_dominance": altcoin_dominance,
        }

    def _format_coin_data(self, coin: dict) -> dict:
        return {
            "name": coin["name"],
            "symbol": coin["symbol"],
            "change": coin["quote"]["USD"]["percent_change_24h"]
        }

    def fetch_fear_and_greed_index(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            fear_and_greed_index = data["data"][0]["value"]
            sentiment = data["data"][0]["value_classification"]

            return fear_and_greed_index, sentiment
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            return None, None

    def send_crypto_market_update(self, market_data: dict, fear_and_greed_index: str, sentiment: str):
        if not market_data:
            return

        current_time = datetime.now().strftime('%H:%M')
        
        crypto_updates = self._build_crypto_updates(market_data["filtered_data"])
        
        gainer_text, loser_text = self._build_gainer_loser_text(market_data)
        
        dominance_text = self._build_dominance_text(market_data["bitcoin_dominance"])
        
        message = (
            f"📈 <b>Crypto Market Update</b>\n\n"
            f"{crypto_updates}\n\n"
            f"{gainer_text}"
            f"{loser_text}"
            f"🌐 Total Market Cap: ${market_data['total_market_cap'] / 1e12:.2f}T\n"
            f"📊 BTC Dominance: {dominance_text}%\n"
            f"📊 ETH Dominance: {market_data['ethereum_dominance']:.2f}%\n"
            f"📊 Altcoin Dominance: {market_data['altcoin_dominance']:.2f}%\n"
            f"😨 Fear & Greed Index: {fear_and_greed_index} ({sentiment})\n\n"
            f"🕒 Sent at: {current_time}"
        )

        self.telegram_client.send_message(message)

    def _build_crypto_updates(self, filtered_data: dict) -> str:
        crypto_updates = []
        
        for symbol, data in filtered_data.items():
            if data['price'] is not None:
                link = self._construct_hyperlink(data['name'])
                price_format = f"${data['price']:.4f}" if data['price'] < 1 else f"${data['price']:.2f}"
                
                emoji, formatted_difference = self._get_price_change_info(symbol, data['price'])
                
                crypto_updates.append(
                    f"{emoji} <a href='{link}'>{data['name']} ({symbol})</a>: {price_format} {formatted_difference}"
                )
        
        return "\n".join(crypto_updates)

    def _get_price_change_info(self, symbol: str, current_price: float) -> Tuple[str, str]:
        emoji = "💰"
        formatted_difference = ""
        
        previous_price = self.previous_prices.get(symbol)
        if previous_price is not None:
            price_difference = current_price - previous_price
            
            if price_difference > 0:
                emoji = "📈"
            elif price_difference < 0:
                emoji = "📉"
            elif price_difference == 0:
                emoji = "➖"
            
            formatted_difference = f"({price_difference:+.4f})" if current_price < 1 else f"({price_difference:+.2f})"
        
        self.previous_prices[symbol] = current_price
        return emoji, formatted_difference

    def _construct_hyperlink(self, name: str) -> str:
        return f"https://www.coinmarketcap.com/currencies/{name.lower().replace(' ', '-')}/"

    def _build_gainer_loser_text(self, market_data: dict) -> Tuple[str, str]:
        gainer_text = ""
        loser_text = ""
        
        if market_data.get("top_gainer"):
            gainer = market_data["top_gainer"]
            gainer_link = self._construct_hyperlink(gainer["name"])
            gainer_text = (
                f"🔥 Top Gainer: <a href='{gainer_link}'>{gainer['name']} ({gainer['symbol']})</a> "
                f"(+{gainer['change']:.2f}%)\n"
            )
        
        if market_data.get("top_loser"):
            loser = market_data["top_loser"]
            loser_link = self._construct_hyperlink(loser["name"])
            loser_text = (
                f"❄️ Top Loser: <a href='{loser_link}'>{loser['name']} ({loser['symbol']})</a> "
                f"({loser['change']:.2f}%)\n\n"
            )
        
        return gainer_text, loser_text

    def _build_dominance_text(self, bitcoin_dominance: float) -> str:
        previous_value = self.previous_dominance.get("btc_dominance")
        
        if previous_value is not None:
            dominance_difference = bitcoin_dominance - previous_value
            formatted_difference = f"{dominance_difference:+.2f}"
            dominance_text = f"{bitcoin_dominance:.2f} ({formatted_difference})"
        else:
            dominance_text = f"{bitcoin_dominance:.2f}"
        
        self.previous_dominance["btc_dominance"] = bitcoin_dominance
        return dominance_text

def monitor_market_updates():
    monitor = CryptoMarketMonitor()
    
    while True:
        try:
            symbols = monitor.data_manager.load_tickers()
            market_data = monitor.fetch_crypto_market_data(symbols)
            fear_and_greed_index, sentiment = monitor.fetch_fear_and_greed_index()

            if market_data:
                monitor.send_crypto_market_update(market_data, fear_and_greed_index, sentiment)

            for remaining in range(config.CRYPTO_UPDATE_INTERVAL, 0, -10):
                minutes, seconds = divmod(remaining, 60)
                logger.info(f"Next market update in: {minutes:02d}:{seconds:02d}")
                time.sleep(10)

        except Exception as e:
            logger.error(f"Error in market monitoring: {e}")
            time.sleep(60)
