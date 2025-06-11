import time
import logging
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from src.utils.telegram_client import TelegramClient
from src.utils.data_manager import DataManager
from config.settings import config

logger = logging.getLogger(__name__)

class PortfolioMonitor:
    def __init__(self):
        self.telegram_client = TelegramClient()
        self.data_manager = DataManager()
        self.previous_values = {}
        self.total_gain_loss = {}
        self.max_retries = 3
        self.retry_delay = 5

    def _setup_chrome_driver(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-search-engine-choice-screen')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
               chrome_driver_path = os.getenv('CHROME_DRIVER_PATH')
        
               if chrome_driver_path and chrome_driver_path.strip() and os.path.exists(chrome_driver_path):
                   logger.info(f"Using ChromeDriver from environment path: {chrome_driver_path}")
                   service = Service(chrome_driver_path)
               else:
                   logger.info("No ChromeDriver path in environment, using WebDriverManager")
                   
                   # Fix for the THIRD_PARTY_NOTICES issue
                   chrome_install = ChromeDriverManager().install()
                   folder = os.path.dirname(chrome_install)
                   chromedriver_path = os.path.join(folder, "chromedriver.exe")
                   service = Service(chromedriver_path)
        
               driver = webdriver.Chrome(service=service, options=options)
               driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
               return driver
        except Exception as e:
           logger.error(f"Failed to setup Chrome driver: {e}")
           raise WebDriverException(f"Chrome driver setup failed: {e}")

    def _safe_extract_text(self, driver: webdriver.Chrome, selectors: List[str], 
                          element_name: str, timeout: int = None) -> Optional[str]:
        timeout = timeout or config.SELENIUM_TIMEOUT
        
        for i, selector in enumerate(selectors):
            try:
                logger.debug(f"Trying {element_name} selector {i+1}/{len(selectors)}: {selector}")
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                text = element.get_attribute("title") or element.text.strip()
                if text:
                    logger.info(f"Successfully extracted {element_name}: {text}")
                    return text
                    
            except (TimeoutException, NoSuchElementException) as e:
                logger.debug(f"{element_name} selector {selector} failed: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {element_name} selector {selector}: {e}")
                continue
        
        logger.error(f"Failed to extract {element_name} with any selector")
        return None

    def _extract_username(self, driver: webdriver.Chrome) -> str:
        selectors = [
            '.UserInfoMenuItemWithTitleAndDesc_user-data-with-title-and-desc__c2iGU h1',
            '.UserInfoMenuItemWithTitleAndDesc_user-data-with-title-and-desc__c2iGU span',
            '[class*="user-data-with-title"] h1',
            '[class*="user-data-with-title"] span',
            'h1[class*="user"]',
            '.username',
            '[data-testid="username"]'
        ]
        
        username = self._safe_extract_text(driver, selectors, "username")
        return username if username else "Unknown"

    def _extract_total_value(self, driver: webdriver.Chrome) -> Optional[float]:
        selectors = [
            '.PortfolioPriceInfo_PT-price-info_price__yirGm',
            '.PortfolioPriceInfo_PT-price-info_price__xjt40',
            '[class^="PortfolioPriceInfo_PT-price-info_price__"]',
            '[class*="PT-price-info_price"]',
            '[class*="price-info"]',
            '.portfolio-value',
            '[data-testid="portfolio-value"]'
        ]

        value_text = self._safe_extract_text(driver, selectors, "total value")
        if not value_text:
            return None
            
        try:
            clean_value = value_text.replace("$", "").replace(",", "").strip()
            if clean_value.startswith("(") and clean_value.endswith(")"):
                clean_value = "-" + clean_value[1:-1]
            return float(clean_value)
        except ValueError as e:
            logger.error(f"Failed to parse total value '{value_text}': {e}")
            return None

    def _extract_percentage_change(self, driver: webdriver.Chrome) -> Optional[float]:
        selectors = [
            '.PortfolioProfitInfo_percentText__kOZnu',
            '.PortfolioProfitInfo_percentText__3NKUK',
            '[class^="PortfolioProfitInfo_percentText__"]',
            '[class*="percentText"]',
            '[class*="percent"]',
            '.percentage-change',
            '[data-testid="percentage-change"]'
        ]
        
        percentage_text = self._safe_extract_text(driver, selectors, "percentage change")
        if not percentage_text:
            return None
            
        try:
            clean_percentage = percentage_text.replace("%", "").strip()
            if clean_percentage.startswith("(") and clean_percentage.endswith(")"):
                clean_percentage = "-" + clean_percentage[1:-1]
            return float(clean_percentage)
        except ValueError as e:
            logger.error(f"Failed to parse percentage change '{percentage_text}': {e}")
            return None
    
    def _extract_money_changed(self, driver: webdriver.Chrome) -> Optional[float]:
        selectors = [
            '.PortfolioProfitInfo_PTProfitInfoPrice__POYqf',
            '.PortfolioProfitInfo_PTProfitInfoPrice__79_kR',
            '[class^="PortfolioProfitInfo_PTProfitInfoPrice__"]',
            '[class*="PTProfitInfoPrice"]',
            '[class*="PortfolioProfitInfo"]',
            '[data-testid="money-change"]',
            '.money-change'
        ]
        
        money_text = self._safe_extract_text(driver, selectors, "money changed")
        if not money_text:
            return None
            
        try:
            clean_money = money_text.replace("$", "").replace(",", "").strip()
            if clean_money.startswith("(") and clean_money.endswith(")"):
                clean_money = "-" + clean_money[1:-1]
            return float(clean_money)
        except ValueError as e:
            logger.error(f"Failed to parse money changed '{money_text}': {e}")
            return None

    def get_portfolio_data_selenium(self, portfolio_url: str) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
        for attempt in range(self.max_retries):
            driver = None
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} for {portfolio_url}")
                driver = self._setup_chrome_driver()
                driver.get(portfolio_url)
                
                time.sleep(config.PAGE_LOAD_DELAY)
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                username = self._extract_username(driver)
                total_value = self._extract_total_value(driver)
                percentage_change = self._extract_percentage_change(driver)
                money_changed = self._extract_money_changed(driver)

                if total_value is not None:
                    return username, total_value, percentage_change, money_changed
                else:
                    logger.warning(f"Failed to get essential data on attempt {attempt + 1}")
                    
            except WebDriverException as e:
                logger.error(f"WebDriver error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception as e:
                        logger.warning(f"Error closing driver: {e}")
            
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to fetch portfolio data after {self.max_retries} attempts")
        return None, None, None, None

    def send_portfolio_update(self, portfolio: dict, username: str, total_value: float, 
                            percentage_change: Optional[float], money_changed: Optional[float]):
        current_time = datetime.now().strftime('%H:%M')
        portfolio_name = portfolio["name"]
        portfolio_url = portfolio["url"]
        threshold = portfolio.get("threshold", 0)

        previous_value = self.previous_values.get(portfolio_name)
        if previous_value is not None:
            value_difference = total_value - previous_value
            self.total_gain_loss[portfolio_name] = self.total_gain_loss.get(portfolio_name, 0) + value_difference
            difference_text = f" ({'+' if value_difference > 0 else ''}{value_difference:.2f})"
        else:
            difference_text = ""
            self.total_gain_loss[portfolio_name] = 0

        self.previous_values[portfolio_name] = total_value

        change_emoji = "📈" if (money_changed or 0) > 0 else "📉"
        
        update_message = (
            f"📊 <b>{username} Update</b>\n"
            f"🔗 <b>Portfolio:</b> {portfolio_name}\n\n"
            f"💰 Current Value: ${total_value:.2f}{difference_text}\n"
        )
        
        if percentage_change is not None:
            update_message += f"{change_emoji} 24h Change: {percentage_change:.2f}%\n"
        
        if money_changed is not None:
            update_message += f"💵 Money Changed: ${money_changed:.2f}\n"
            
        update_message += (
            f"📊 Total Gain/Loss: ${self.total_gain_loss[portfolio_name]:.2f}\n\n"
            f"🕒 Updated at: {current_time}"
        )

        try:
            self.telegram_client.send_message(update_message)
            
            if threshold > 0 and total_value >= threshold:
                self.send_threshold_alert(username, portfolio_name, total_value, threshold, current_time)
                
        except Exception as e:
            logger.error(f"Failed to send portfolio update: {e}")

    def send_threshold_alert(self, username: str, portfolio_name: str, 
                           total_value: float, threshold: float, current_time: str):
        alert_message = (
            f"🚀 <b>THRESHOLD ALERT</b>\n"
            f"👤 <b>User:</b> {username}\n"
            f"📊 <b>Portfolio:</b> {portfolio_name}\n\n"
            f"💰 Current Value: ${total_value:.2f}\n"
            f"⚠️ Threshold of ${threshold:.2f} reached!\n"
            f"🕒 Alert time: {current_time}"
        )
        
        try:
            for i in range(3):
                self.telegram_client.send_message(alert_message)
                if i < 2:
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to send threshold alert: {e}")

def monitor_portfolios():
    monitor = PortfolioMonitor()
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    logger.info("Starting portfolio monitoring...")
    
    while True:
        try:
            portfolios = monitor.data_manager.load_portfolios()
            
            if not portfolios:
                logger.warning("No portfolios found to monitor")
                time.sleep(60)
                continue
            
            successful_updates = 0
            
            for portfolio in portfolios:
                try:
                    portfolio_url = portfolio["url"]
                    portfolio_name = portfolio["name"]
                    
                    logger.info(f"Checking portfolio: {portfolio_name}")
                    
                    username, total_value, percentage_change, money_changed = monitor.get_portfolio_data_selenium(portfolio_url)

                    if total_value is not None:
                        monitor.send_portfolio_update(
                            portfolio, username, total_value, percentage_change, money_changed
                        )
                        successful_updates += 1
                    else:
                        logger.warning(f"Failed to get data for portfolio: {portfolio_name}")

                except Exception as e:
                    logger.error(f"Error monitoring portfolio {portfolio.get('name', 'Unknown')}: {e}")
                
                time.sleep(2)
            
            if successful_updates > 0:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                
            if consecutive_failures >= max_consecutive_failures:
                logger.critical(f"Too many consecutive failures ({consecutive_failures}). Taking longer break.")
                time.sleep(300)
                consecutive_failures = 0

            for remaining in range(config.PORTFOLIO_UPDATE_INTERVAL, 0, -10):
                minutes, seconds = divmod(remaining, 60)
                logger.info(f"Next update in: {minutes:02d}:{seconds:02d}")
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            break
        except Exception as e:
            logger.error(f"Critical error in portfolio monitoring: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_portfolios()
