import json
import os
from typing import List, Dict, Any
from config.settings import config

class DataManager:
    @staticmethod
    def ensure_data_directory():
        os.makedirs("data", exist_ok=True)
    
    @staticmethod
    def load_portfolios() -> List[Dict[str, Any]]:
        DataManager.ensure_data_directory()
        try:
            with open(config.PORTFOLIOS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    @staticmethod
    def load_tickers() -> List[str]:
        DataManager.ensure_data_directory()
        try:
            with open(config.TICKERS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    @staticmethod
    def save_data(portfolios: List[Dict], tickers: List[str]):
        DataManager.ensure_data_directory()
        
        with open(config.PORTFOLIOS_FILE, "w") as f:
            json.dump(portfolios, f, indent=4)
        
        with open(config.TICKERS_FILE, "w") as f:
            json.dump(tickers, f, indent=4)
