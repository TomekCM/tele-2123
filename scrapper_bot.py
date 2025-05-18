import os
import json
import time
import logging
import random
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import quote
import aiohttp
import traceback
import asyncio
from selenium import webdriver
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Dict, List, Tuple, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 600  # секунд (10 минут)
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
TWITTER_BEARER = os.getenv("TWITTER_BEARER", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.lacontrevoie.fr",
    "https://nitter.unixfox.eu",
    "https://nitter.fdn.fr",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
    "https://nitter.mint.lgbt",
    "https://nitter.privacy.com.de",
    "https://nitter.projectsegfau.lt",
    "https://nitter.privacydev.net",
    "https://tweet.lambda.dance",
    "https://tweet.namejeff.xyz"
]

DATA_DIR = "data"
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
API_LIMITS_FILE = os.path.join(DATA_DIR, "api_limits.json")
PROXIES_FILE = os.path.join(DATA_DIR, "proxies.json")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")
BROWSER_STATS_FILE = os.path.join(DATA_DIR, "browser_stats.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Глобальная переменная для отслеживания экземпляра Safari WebDriver
safari_driver = None


def twitter_login_with_google(email, password):
    """Полностью автоматизированный вход в Twitter через Google"""
    global safari_driver

    try:
        logger.info("Запускаем автоматическую авторизацию в Twitter через Google...")

        # Закрываем существующий Safari, если он открыт
        subprocess.run(['killall', 'Safari'], check=False)
        time.sleep(1)

        # Инициализируем новый WebDriver
        try:
            options = SafariOptions()
            safari_driver = webdriver.Safari(options=options)
            safari_driver.set_page_load_timeout(30)
            safari_driver.implicitly_wait(15)  # Увеличиваем время ожидания
            logger.info("Safari WebDriver инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Safari WebDriver: {e}")
            return False

        # Открываем страницу логина Twitter
        try:
            safari_driver.get("https://twitter.com/i/flow/login")
            logger.info("Открыта страница логина Twitter")

            # Даем странице полностью загрузиться
            time.sleep(10)  # Увеличиваем задержку до 10 секунд

            # Сделаем скриншот для диагностики
            safari_driver.save_screenshot("/tmp/twitter_login_page.png")
            logger.info("Сделан скриншот страницы логина: /tmp/twitter_login_page.png")

        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы Twitter: {e}")
            return False

        # Шаг 1: Нажимаем на кнопку "Sign in with Google" - УЛУЧШЕННЫЙ АЛГОРИТМ
        try:
            # Первая попытка - более прямой JavaScript для поиска кнопок
            buttons_found = safari_driver.execute_script("""
                // Создаем массив для хранения найденных кнопок
                let possibleButtons = [];

                // Метод 1: По тексту
                document.querySelectorAll('div[role="button"]').forEach(el => {
                    if (el.textContent && el.textContent.toLowerCase().includes('google')) {
                        possibleButtons.push(el);
                    }
                });

                // Метод 2: По атрибутам
                document.querySelectorAll('div[data-testid]').forEach(el => {
                    if (el.getAttribute('data-testid').includes('google')) {
                        possibleButtons.push(el);
                    }
                });

                // Метод 3: По классам
                document.querySelectorAll('div').forEach(el => {
                    if (el.className && el.className.includes('google')) {
                        possibleButtons.push(el);
                    }
                });

                // Метод 4: Поиск брендовых элементов
                document.querySelectorAll('img, svg').forEach(el => {
                    if (el.alt && el.alt.toLowerCase().includes('google')) {
                        possibleButtons.push(el.parentElement);
                    }
                });

                // Возвращаем количество найденных кнопок
                return possibleButtons.length;
            """)

            logger.info(f"Найдено потенциальных Google кнопок: {buttons_found}")

            # Метод 5: Прямое нажатие через JavaScript, если нашли кнопки
            if buttons_found > 0:
                clicked = safari_driver.execute_script("""
                    // Пытаемся найти кнопку Google
                    let possibleButtons = [];

                    // Метод 1: По тексту
                    document.querySelectorAll('div[role="button"]').forEach(el => {
                        if (el.textContent && el.textContent.toLowerCase().includes('google')) {
                            possibleButtons.push(el);
                        }
                    });

                    // Метод 2: По атрибутам
                    document.querySelectorAll('div[data-testid]').forEach(el => {
                        if (el.getAttribute('data-testid').includes('google')) {
                            possibleButtons.push(el);
                        }
                    });

                    // Метод 3: По классам
                    document.querySelectorAll('div').forEach(el => {
                        if (el.className && el.className.includes('google')) {
                            possibleButtons.push(el);
                        }
                    });

                    // Метод 4: Поиск брендовых элементов
                    document.querySelectorAll('img, svg').forEach(el => {
                        if (el.alt && el.alt.toLowerCase().includes('google')) {
                            possibleButtons.push(el.parentElement);
                        }
                    });

                    // Нажимаем на первую найденную кнопку
                    if (possibleButtons.length > 0) {
                        possibleButtons[0].click();
                        return true;
                    }

                    return false;
                """)

                if clicked:
                    logger.info("Нажали на кнопку входа через Google с помощью JavaScript")
                    time.sleep(5)  # Ждем переход на страницу Google
                else:
                    logger.warning("Не удалось нажать на кнопку через JavaScript")
            else:
                logger.warning("Не найдены потенциальные кнопки Google через JavaScript")

            # Резервный метод - пробуем через Selenium
            if not buttons_found or not clicked:
                logger.info("Пробуем найти кнопку Google с помощью Selenium...")

                # Ищем по разным признакам
                possible_button_xpaths = [
                    # 1. Поиск по тексту
                    "//div[contains(translate(., 'GOOGLE', 'google'), 'google')]",
                    "//span[contains(translate(., 'GOOGLE', 'google'), 'google')]",

                    # 2. Поиск по атрибутам
                    "//div[@data-testid and contains(@data-testid, 'google')]",

                    # 3. Более общие селекторы
                    "//div[@role='button']",
                    "//div[contains(@class, 'Button')]",

                    # 4. Поиск по соседним элементам
                    "//*[contains(@src, 'google')]/ancestor::div[@role='button']",
                    "//*[contains(@alt, 'google')]/ancestor::div[@role='button']"
                ]

                for xpath in possible_button_xpaths:
                    try:
                        buttons = safari_driver.find_elements(By.XPATH, xpath)
                        logger.info(f"Селектор {xpath}: найдено {len(buttons)} элементов")

                        for i, button in enumerate(buttons):
                            if i < 3:  # Проверяем только первые 3 кнопки для каждого селектора
                                try:
                                    button_text = button.text.lower()
                                    logger.info(f"Кнопка {i + 1}: текст = '{button_text}'")

                                    if "google" in button_text:
                                        # Скроллинг к кнопке для уверенности
                                        safari_driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                        time.sleep(1)

                                        # Пробуем нажать с помощью JavaScript
                                        safari_driver.execute_script("arguments[0].click();", button)
                                        logger.info(f"Нажали на кнопку Google через Selenium (xpath: {xpath})")
                                        time.sleep(5)

                                        # Проверяем, был ли переход на Google
                                        current_url = safari_driver.current_url
                                        if "accounts.google.com" in current_url:
                                            logger.info(f"Успешный переход на Google: {current_url}")
                                            return True
                                        else:
                                            logger.info(f"После нажатия URL: {current_url}")
                                except:
                                    pass
                    except:
                        pass

                # Делаем скриншот для анализа
                safari_driver.save_screenshot("/tmp/twitter_no_google_button.png")
                logger.error("Не удалось найти и нажать кнопку Google")
                return False

        except Exception as e:
            logger.error(f"Ошибка при поиске кнопки входа через Google: {e}")
            safari_driver.save_screenshot("/tmp/twitter_button_error.png")
            return False

        # Если мы дошли сюда, значит, возможно, мы нажали на кнопку
        # Проверяем переход на страницу Google
        time.sleep(5)
        current_url = safari_driver.current_url

        logger.info(f"Текущий URL после попытки нажатия: {current_url}")
        safari_driver.save_screenshot("/tmp/after_button_click.png")

        # Дальнейший код для ввода учетных данных Google...
        # (остальной код остается без изменений)

    except Exception as e:
        logger.error(f"Общая ошибка при авторизации через Google: {e}")
        if safari_driver:
            safari_driver.save_screenshot("/tmp/twitter_login_error.png")
        return False

def update_browser_stats(browser_name, action_type, success):
    """Обновляет статистику использования браузеров"""
    try:
        if os.path.exists(BROWSER_STATS_FILE):
            with open(BROWSER_STATS_FILE, 'r') as f:
                stats = json.load(f)
        else:
            stats = {"browsers": {}, "last_update": int(time.time())}

        # Инициализируем данные для браузера, если их нет
        if browser_name not in stats["browsers"]:
            stats["browsers"][browser_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "captchas": 0,
                "errors": 0,
                "last_success": None
            }

        # Обновляем статистику
        stats["browsers"][browser_name]["total_attempts"] += 1

        if action_type == "captcha":
            stats["browsers"][browser_name]["captchas"] += 1

        if action_type == "error":
            stats["browsers"][browser_name]["errors"] += 1

        if success:
            stats["browsers"][browser_name]["successful_attempts"] += 1
            stats["browsers"][browser_name]["last_success"] = int(time.time())

        stats["last_update"] = int(time.time())

        with open(BROWSER_STATS_FILE, 'w') as f:
            json.dump(stats, f)

    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики браузеров: {e}")


class HTMLSession:
    """Класс для работы с Safari WebDriver с возможностью паузы для ручного ввода капчи"""

    def __init__(self):
        global safari_driver
        self.browser_name = "Safari"

        try:
            # Создаем один раз и переиспользуем
            if safari_driver is None:
                logger.info("Создание экземпляра Safari WebDriver")
                options = SafariOptions()
                safari_driver = webdriver.Safari(options=options)
                safari_driver.set_page_load_timeout(25)
                safari_driver.implicitly_wait(10)

            self.driver = safari_driver
            logger.info("Используем существующий экземпляр Safari")

        except Exception as e:
            logger.error(f"Не удалось инициализировать Safari: {e}")
            raise

    def get(self, url, proxies=None, timeout=25):
        """Загружает страницу через Safari WebDriver"""
        try:
            logger.info(f"Загружаю страницу через Safari: {url}")
            self.driver.get(url)
            time.sleep(5)  # Даем время для загрузки

            # Проверяем наличие капчи
            if self.has_captcha():
                self.pause_for_captcha()

            return self
        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы {url}: {e}")
            return self

    def has_captcha(self):
        """Проверяет наличие капчи на странице"""
        try:
            page_source = self.driver.page_source.lower()
            captcha_indicators = ['captcha', 'i am not a robot', 'я не робот', 'проверка безопасности']

            for indicator in captcha_indicators:
                if indicator in page_source:
                    logger.info("Обнаружена проверка капчи!")
                    return True

            return False
        except:
            return False

    def pause_for_captcha(self):
        """Останавливает выполнение и показывает инструкции для ручного решения капчи"""
        logger.info("Пауза для ручного ввода капчи - нажмите 'Continue Session' в Safari")

        # Показываем уведомление на экране macOS
        try:
            subprocess.run([
                'osascript',
                '-e',
                'display notification "Пожалуйста, решите капчу и нажмите Continue Session" with title "Требуется ввод капчи"'
            ])
        except:
            pass

        # Пауза для решения капчи пользователем
        print("\n" + "=" * 50)
        print("ВНИМАНИЕ! Обнаружена КАПЧА!")
        print("1. В окне Safari нажмите кнопку 'Continue Session'")
        print("2. Решите капчу вручную")
        print("3. После решения капчи работа продолжится автоматически")
        print("=" * 50 + "\n")

        # Ждем 30 секунд для решения капчи
        time.sleep(30)

    @property
    def html(self):
        return self.driver

    def close(self):
        """Не закрывает Safari, только освобождает ресурсы"""
        # НЕ ЗАКРЫВАЕМ драйвер!
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def is_admin(user_id):
    settings = get_settings()
    admin_ids = settings.get('admin_ids', [])
    return user_id in admin_ids or user_id == ADMIN_ID


def init_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        save_json(ACCOUNTS_FILE, {})
        return {}

    accounts = load_json(ACCOUNTS_FILE, {})

    if isinstance(accounts, list):
        logger.info("Мигрируем аккаунты из списка в словарь")
        new_accounts = {}
        for account in accounts:
            username = account.get("username", "")
            if username:
                new_accounts[username.lower()] = {
                    "username": username,
                    "added_at": account.get("added_at", datetime.now().isoformat()),
                    "last_check": account.get("last_check"),
                    "last_tweet_id": None,
                    "check_count": 0,
                    "success_rate": 100.0,
                    "fail_count": 0,
                    "check_method": None,
                    "priority": 1.0,
                    "first_check": True
                }
        save_json(ACCOUNTS_FILE, new_accounts)
        return new_accounts

    updated = False
    for username, account in accounts.items():
        if "check_count" not in account:
            account["check_count"] = 0
            updated = True
        if "success_rate" not in account:
            account["success_rate"] = 100.0
            updated = True
        if "fail_count" not in account:
            account["fail_count"] = 0
            updated = True
        if "check_method" not in account:
            account["check_method"] = None
            updated = True
        if "priority" not in account:
            account["priority"] = 1.0
            updated = True
        if "first_check" not in account:
            account["first_check"] = True
            updated = True
        if "last_tweet_text" not in account:
            account["last_tweet_text"] = ""
            updated = True
        if "last_tweet_url" not in account:
            account["last_tweet_url"] = ""
            updated = True
        if "tweet_data" not in account:
            account["tweet_data"] = {}
            updated = True
        if "scraper_methods" not in account:
            account["scraper_methods"] = None
            updated = True

    if updated:
        save_json(ACCOUNTS_FILE, accounts)

    return accounts


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла {path}: {e}")


def save_accounts(accounts_data):
    save_json(ACCOUNTS_FILE, accounts_data)

def display_captcha_notification():
    """Отображает системное уведомление о капче"""
    try:
        subprocess.run([
            'osascript',
            '-e',
            'display notification "Пожалуйста, решите капчу в окне Safari" with title "Требуется ввод капчи" sound name "Submarine"'
        ])
    except:
        pass

def get_cache():
    cache = load_json(CACHE_FILE, {"tweets": {}, "users": {}, "timestamp": int(time.time())})

    current_time = int(time.time())
    hours_ago = current_time - 21600  # 6 часов

    tweets_cache = cache.get("tweets", {})
    for username, data in list(tweets_cache.items()):
        if data.get("timestamp", 0) < hours_ago:
            del tweets_cache[username]

    users_cache = cache.get("users", {})
    for username, data in list(users_cache.items()):
        if data.get("timestamp", 0) < hours_ago:
            del users_cache[username]

    cache["timestamp"] = current_time
    return cache


def update_cache(category, key, data, force=False):
    cache = get_cache()

    if category not in cache:
        cache[category] = {}

    # Если нужно сохранить историю
    if category == "tweets" and key in cache[category] and not force:
        # Получаем текущие данные
        current_data = cache[category][key].get("data", {})
        current_tweet_id = current_data.get("tweet_id")

        # Если новые данные содержат новый ID твита, сохраняем старые в историю
        if data and "tweet_id" in data and current_tweet_id and data["tweet_id"] != current_tweet_id:
            # Создаем или обновляем историю
            if "history" not in cache[category][key]:
                cache[category][key]["history"] = []

            # Добавляем текущие данные в историю (ограничиваем до 10 записей)
            history_entry = {
                "tweet_id": current_tweet_id,
                "tweet_data": current_data.get("tweet_data", {}),
                "timestamp": cache[category][key].get("timestamp", int(time.time()))
            }

            history = cache[category][key]["history"]
            history.append(history_entry)

            # Ограничиваем размер истории
            if len(history) > 10:
                history = history[-10:]

            cache[category][key]["history"] = history

    # Принудительное удаление старого значения
    if force and key in cache[category]:
        del cache[category][key]

    # Добавляем новые данные с текущим временем
    if data is not None:
        cache[category][key] = {
            "data": data,
            "timestamp": int(time.time())
        }

    save_json(CACHE_FILE, cache)


def get_from_cache(category, key, max_age=300):
    cache = get_cache()

    if category in cache and key in cache[category]:
        item = cache[category][key]
        if int(time.time()) - item.get("timestamp", 0) < max_age:
            return item.get("data")

    return None


def delete_from_cache(category=None, key=None):
    cache = get_cache()

    if category is None:
        cache = {"tweets": {}, "users": {}, "timestamp": int(time.time())}
        logger.info("Полная очистка кеша")
    elif key is None and category in cache:
        cache[category] = {}
        logger.info(f"Очищен кеш раздела {category}")
    elif category in cache and key in cache[category]:
        del cache[category][key]
        logger.info(f"Удалена запись {key} из кеша {category}")

    save_json(CACHE_FILE, cache)


def get_settings():
    settings = load_json(SETTINGS_FILE, {
        "check_interval": DEFAULT_CHECK_INTERVAL,
        "enabled": True,
        "use_proxies": False,
        "scraper_methods": ["nitter", "web", "api"],
        "max_retries": 3,
        "cache_expiry": 1800,
        "randomize_intervals": True,
        "min_interval_factor": 0.8,
        "max_interval_factor": 1.2,
        "parallel_checks": 3,
        "api_request_limit": 20,
        "nitter_instances": NITTER_INSTANCES,
        "health_check_interval": 3600,
        "last_health_check": 0
    })

    if "api_request_limit" not in settings or not isinstance(settings["api_request_limit"], int):
        settings["api_request_limit"] = 20
        save_json(SETTINGS_FILE, settings)

    return settings


def update_setting(key, value):
    settings = get_settings()
    settings[key] = value
    save_json(SETTINGS_FILE, settings)
    return settings


def get_proxies():
    return load_json(PROXIES_FILE, {"proxies": []})


def get_random_proxy():
    proxies_data = get_proxies()
    proxy_list = proxies_data.get("proxies", [])

    if not proxy_list:
        return None

    proxy = random.choice(proxy_list)
    if proxy.startswith("http"):
        return {"http": proxy, "https": proxy}
    else:
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}


def clean_account_data(username):
    logger.info(f"Очистка всех данных для аккаунта @{username}")

    delete_from_cache("tweets", f"api_{username.lower()}")
    delete_from_cache("tweets", f"web_{username.lower()}")
    delete_from_cache("tweets", f"nitter_{username.lower()}")
    delete_from_cache("users", username.lower())

    accounts = init_accounts()
    if username.lower() in accounts:
        accounts[username.lower()] = {
            "username": accounts[username.lower()].get("username", username),
            "added_at": datetime.now().isoformat(),
            "last_check": None,
            "last_tweet_id": None,
            "check_count": 0,
            "success_rate": 100.0,
            "fail_count": 0,
            "check_method": None,
            "priority": 1.0,
            "first_check": True,
            "last_tweet_text": "",
            "last_tweet_url": "",
            "tweet_data": {},
            "scraper_methods": accounts[username.lower()].get("scraper_methods", None)  # Сохраняем настройки методов
        }
        save_accounts(accounts)

    logger.info(f"Данные для аккаунта @{username} очищены")


def launch_safari_for_scraping():
    """Открывает существующий Safari с Twitter для скрапинга"""
    if platform.system() != "Darwin":  # Проверка что это macOS
        logger.error("Safari доступен только на macOS")
        return False

    try:
        # Проверяем запущен ли Safari
        applescript = '''
        tell application "System Events"
            set safariRunning to exists (processes where name is "Safari")
        end tell
        '''

        result = subprocess.run(['osascript', '-e', applescript],
                                check=True, capture_output=True, text=True)

        if "true" not in result.stdout.lower():
            # Safari не запущен, открываем его с Twitter
            subprocess.run(['open', '-a', 'Safari', 'https://twitter.com/home'], check=True)
            logger.info("Safari с Twitter запущен")
            time.sleep(2)
        else:
            # Safari запущен, открываем Twitter в текущем окне
            applescript = '''
            tell application "Safari"
                set URL of current tab of window 1 to "https://twitter.com/home"
            end tell
            '''
            subprocess.run(['osascript', '-e', applescript], check=True)
            logger.info("Twitter открыт в существующем окне Safari")

        return True
    except Exception as e:
        logger.error(f"Ошибка при открытии Safari: {e}")
        traceback.print_exc()
        return False


def twitter_login_with_google(email, password):
    """Автоматизированный вход в Twitter через Google"""
    global safari_driver

    try:
        logger.info("Запускаем авторизацию в Twitter через Google...")

        # Закрываем существующий Safari если он открыт
        subprocess.run(['killall', 'Safari'], check=False)
        time.sleep(1)

        # Инициализируем новый WebDriver
        try:
            options = SafariOptions()
            safari_driver = webdriver.Safari(options=options)
            safari_driver.set_page_load_timeout(30)
            safari_driver.implicitly_wait(10)
            logger.info("Safari WebDriver инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Safari WebDriver: {e}")
            return False

        # Открываем страницу логина Twitter
        try:
            safari_driver.get("https://twitter.com/i/flow/login")
            logger.info("Открыта страница логина Twitter")
            time.sleep(7)  # Достаточное время для загрузки
        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы Twitter: {e}")
            return False

        # НОВЫЙ КОД: Максимально точный поиск кнопки Google по её внешнему виду
        try:
            # Специфичные XPath выражения, точно соответствующие кнопке с изображения
            google_button_xpaths = [
                # По точному тексту "Sign in with Google" (наиболее точный селектор)
                "//span[text()='Sign in with Google']/ancestor::div[@role='button']",

                # По частичному совпадению текста
                "//span[contains(text(), 'Sign in with Google')]/ancestor::div[@role='button']",
                "//div[@role='button'][contains(., 'Google')]",

                # По SVG или IMG логотипу Google (если текст не работает)
                "//img[contains(@alt, 'Google')]/ancestor::div[@role='button']",
                "//svg[contains(@aria-label, 'Google')]/ancestor::div[@role='button']",

                # По содержимому, используя translate для регистронезависимого поиска
                "//div[@role='button'][contains(translate(., 'GOOGLE', 'google'), 'google')]",

                # По атрибуту data-testid (если он есть)
                "//div[@data-testid='oauth_button_google']",
                "//div[contains(@data-testid, 'google')]"
            ]

            # Перебираем все селекторы до первого рабочего
            for xpath in google_button_xpaths:
                try:
                    buttons = safari_driver.find_elements(By.XPATH, xpath)
                    if buttons:
                        for button in buttons:
                            # Проверяем, что кнопка видима
                            if button.is_displayed():
                                # Прокручиваем к кнопке и делаем скриншот для проверки
                                safari_driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(1)
                                safari_driver.save_screenshot("/tmp/found_google_button.png")

                                # Пробуем нажать кнопку через JavaScript для надежности
                                safari_driver.execute_script("arguments[0].click();", button)
                                logger.info(f"Успешно нажали на кнопку Google через XPath: {xpath}")
                                time.sleep(5)  # Ждем реакции после нажатия

                                # Проверяем, изменился ли URL
                                if "accounts.google.com" in safari_driver.current_url:
                                    logger.info("Переход на страницу Google подтвержден")
                                    break
                                else:
                                    logger.info(f"После нажатия URL: {safari_driver.current_url}")
                                    continue
                except Exception as e:
                    logger.debug(f"Селектор {xpath} не сработал: {e}")
                    continue

            # Если предыдущие методы не сработали, используем поиск по CSS
            if "accounts.google.com" not in safari_driver.current_url:
                logger.info("Пробуем найти кнопку Google через CSS селекторы...")

                # CSS селекторы для белой кнопки Google
                css_selectors = [
                    "div[role='button'] span:contains('Google')",
                    ".google-sign-in",
                    "div[role='button']:has(span:contains('Google'))",
                    "button:has(img[alt*='Google'])",
                    "div.r-jwli3a:has(span:contains('Google'))"  # Специфичный класс Twitter
                ]

                for selector in css_selectors:
                    try:
                        # Используем JavaScript для поиска по CSS, поскольку ":contains" не поддерживается Selenium
                        button_found = safari_driver.execute_script(f"""
                            const btn = document.querySelector('{selector}');
                            if (btn) {{
                                btn.click();
                                return true;
                            }}
                            return false;
                        """)

                        if button_found:
                            logger.info(f"Нажали кнопку через JavaScript с CSS: {selector}")
                            time.sleep(5)
                            break
                    except:
                        continue

            # Последний вариант - прямое нажатие через JavaScript по тексту
            if "accounts.google.com" not in safari_driver.current_url:
                direct_js = """
                const buttons = Array.from(document.querySelectorAll('div[role="button"], button'));
                for (const btn of buttons) {
                    if (btn.innerText && btn.innerText.includes('Google')) {
                        btn.click();
                        return true;
                    }
                }

                // Также ищем по изображениям
                const googleImgs = Array.from(document.querySelectorAll('img[alt*="Google"], svg[aria-label*="Google"]'));
                for (const img of googleImgs) {
                    const parent = img.closest('div[role="button"], button');
                    if (parent) {
                        parent.click();
                        return true;
                    }
                }
                return false;
                """
                google_button_clicked = safari_driver.execute_script(direct_js)
                if google_button_clicked:
                    logger.info("Нажали кнопку Google через прямой JavaScript поиск")
                    time.sleep(5)

            # Проверяем, удалось ли нажать на кнопку
            if "accounts.google.com" not in safari_driver.current_url:
                logger.error("Не удалось перейти на страницу Google авторизации")
                safari_driver.save_screenshot("/tmp/twitter_no_transition.png")
                return False

        except Exception as e:
            logger.error(f"Ошибка при поиске кнопки Google: {e}")
            safari_driver.save_screenshot("/tmp/twitter_button_error.png")
            return False

        # Нажимаем на кнопку "Sign in with Google"
        try:
            google_button = safari_driver.find_element(By.XPATH,
                                                       "//div[contains(@role, 'button')][.//div[contains(@dir, 'auto')][contains(text(), 'Google')]]")
            google_button.click()
            logger.info("Нажали кнопку входа через Google")
            time.sleep(5)  # Ждем переключения на окно Google
        except Exception as e:
            logger.error(f"Не удалось найти кнопку входа через Google: {e}")
            return False

        # Проверяем и используем окно Google
        current_window = safari_driver.current_window_handle
        all_windows = safari_driver.window_handles

        # Если открылось новое окно, переключаемся на него
        if len(all_windows) > 1:
            for window in all_windows:
                if window != current_window:
                    safari_driver.switch_to.window(window)
                    break

        # Вводим email
        try:
            email_input = safari_driver.find_element(By.XPATH, "//input[@type='email']")
            email_input.send_keys(email)

            # Нажимаем "Далее"/"Next"
            next_button = safari_driver.find_element(By.XPATH,
                                                     "//div[contains(@role, 'button')]//span[contains(text(), 'Next')]/..")
            if not next_button:
                next_button = safari_driver.find_element(By.XPATH, "//button[@type='button'][contains(., 'Next')]")
            next_button.click()
            logger.info("Ввели email, нажали Next")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Ошибка при вводе email: {e}")
            return False

        # Вводим пароль
        try:
            password_input = safari_driver.find_element(By.XPATH, "//input[@type='password']")
            password_input.send_keys(password)

            # Нажимаем кнопку входа
            login_button = safari_driver.find_element(By.XPATH,
                                                      "//div[contains(@role, 'button')]//span[contains(text(), 'Next')]/..")
            if not login_button:
                login_button = safari_driver.find_element(By.XPATH, "//button[@type='button'][contains(., 'Next')]")
            login_button.click()
            logger.info("Ввели пароль, нажали кнопку входа")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Ошибка при вводе пароля: {e}")
            return False

        # Проверка успешной авторизации (ждем перенаправления на Twitter)
        wait_time = 0
        while wait_time < 30:  # Ждем максимум 30 секунд
            if "twitter.com/home" in safari_driver.current_url:
                logger.info("Успешная авторизация в Twitter через Google!")
                return True
            time.sleep(1)
            wait_time += 1

        logger.warning("Превышено время ожидания перенаправления на Twitter")
        return False

    except Exception as e:
        logger.error(f"Ошибка при авторизации через Google: {e}")
        return False


def login_with_regular_safari():
    """Запускает обычный Safari и выполняет вход через Google"""
    try:
        # Закрываем Safari если он уже открыт
        subprocess.run(['killall', 'Safari'], check=False)
        time.sleep(1)

        # Открываем Twitter в обычном Safari
        subprocess.run(['open', '-a', 'Safari', 'https://twitter.com/i/flow/login'], check=True)
        time.sleep(5)

        # Нажимаем на Google кнопку через AppleScript
        applescript = '''
        tell application "Safari"
            activate
            delay 5

            -- Находим и нажимаем на кнопку Google
            do JavaScript "
                function findAndClickGoogleButton() {
                    // Ищем кнопку по тексту
                    const allElements = document.querySelectorAll('div[role=\\"button\\"], button, a');
                    for (const el of allElements) {
                        if (el.textContent && el.textContent.includes('Google')) {
                            el.click();
                            return 'Нашли и нажали по тексту';
                        }
                    }

                    // Ищем по изображениям Google
                    const images = document.querySelectorAll('img, svg');
                    for (const img of images) {
                        if ((img.alt && img.alt.includes('Google')) || 
                            (img.getAttribute('aria-label') && img.getAttribute('aria-label').includes('Google'))) {
                            const parent = img.closest('div[role=\\"button\\"], button, a');
                            if (parent) {
                                parent.click();
                                return 'Нашли и нажали через изображение';
                            }
                        }
                    }

                    return 'Кнопка Google не найдена';
                }
                return findAndClickGoogleButton();
            "
        end tell
        '''

        result = subprocess.run(['osascript', '-e', applescript],
                                capture_output=True, text=True)

        print(f"Результат поиска кнопки: {result.stdout}")

        return "нажали" in result.stdout.lower() or "button" in result.stdout.lower()

    except Exception as e:
        print(f"Ошибка при запуске Safari: {e}")
        return False

class TwitterClient:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.rate_limited = False
        self.rate_limit_reset = 0
        self.user_agent = UserAgent().random
        self.cache = {}
        self.session = requests.Session()
        # Отключаем проверку SSL для решения проблем с сертификатами
        self.session.verify = False
        # Подавляем предупреждения о небезопасных запросах
        import urllib3
        urllib3.disable_warnings()

    def clear_cache(self):
        self.cache = {}

    def update_user_agent(self):
        self.user_agent = UserAgent().random

    def check_rate_limit(self):
        if self.rate_limited:
            now = time.time()
            if now < self.rate_limit_reset:
                return False
            else:
                self.rate_limited = False
        return True

    def set_rate_limit(self, reset_time):
        self.rate_limited = True
        self.rate_limit_reset = reset_time

        limits = load_json(API_LIMITS_FILE, {})
        limits["twitter_api"] = {
            "rate_limited": True,
            "reset_time": reset_time,
            "updated_at": int(time.time())
        }
        save_json(API_LIMITS_FILE, limits)

    def get_user_by_username(self, username):
        if not self.bearer_token or not self.check_rate_limit():
            return None

        cached_user = get_from_cache("users", username.lower(), 86400)
        if cached_user:
            return cached_user

        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.user_agent
        }

        try:
            response = self.session.get(url, headers=headers, timeout=10)

            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 900))
                self.set_rate_limit(reset_time)
                remaining = int(response.headers.get("x-rate-limit-remaining", 0))
                limit = int(response.headers.get("x-rate-limit-limit", 0))
                logger.warning(
                    f"API лимит пользователей: {remaining}/{limit}. Сброс в {reset_time}"
                )
                return None

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    update_cache("users", username.lower(), data["data"])
                    return data["data"]
            else:
                logger.error(f"Ошибка при получении пользователя: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Ошибка запроса к API: {e}")

        return None

    def get_user_id(self, username, use_proxies=False):
        """Получает Twitter ID пользователя по имени аккаунта"""
        logger.info(f"Запрос ID пользователя для @{username}...")

        # Проверяем кеш пользователя
        cached_user_data = get_from_cache("users", username.lower(), 86400)  # Кеш на 24 часа
        if cached_user_data and "id" in cached_user_data:
            logger.info(f"ID пользователя @{username} найден в кеше: {cached_user_data['id']}")
            return cached_user_data["id"]

        # Проверяем лимиты API
        if not self.bearer_token or not self.check_rate_limit():
            return None

        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.user_agent
        }

        try:
            proxies = get_random_proxy() if use_proxies else None
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=10)

            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 900))
                self.set_rate_limit(reset_time)
                remaining = int(response.headers.get("x-rate-limit-remaining", 0))
                limit = int(response.headers.get("x-rate-limit-limit", 0))
                logger.warning(
                    f"API лимит запросов: {remaining}/{limit}. Сброс в {reset_time}"
                )
                return None

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "id" in data["data"]:
                    user_id = data["data"]["id"]
                    # Сохраняем в кеш с данными пользователя
                    update_cache("users", username.lower(), data["data"])
                    logger.info(f"Получен ID пользователя @{username}: {user_id}")
                    return user_id
                else:
                    logger.warning(f"ID пользователя @{username} не найден в ответе API")
                    return None
            else:
                logger.warning(f"Ошибка API {response.status_code} при запросе ID @{username}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при получении ID пользователя @{username}: {e}")
            return None

    def get_user_tweets(self, user_id, use_proxies=False):
        # Проверяем нужно ли вообще делать запрос к API
        if not self.bearer_token or not self.check_rate_limit():
            return None

        settings = get_settings()
        api_request_limit = settings.get("api_request_limit", 20)
        logger.info(f"Запрос твитов для user_id={user_id}, лимит API: {api_request_limit}")

        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": api_request_limit,
            "tweet.fields": "created_at,text,attachments,public_metrics",
            "exclude": "retweets,replies",
            "expansions": "attachments.media_keys",
            "media.fields": "type,url,preview_image_url"
        }
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.user_agent
        }

        try:
            proxies = get_random_proxy() if use_proxies else None
            response = self.session.get(url, headers=headers, params=params, proxies=proxies, timeout=10)

            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 900))
                self.set_rate_limit(reset_time)
                remaining = int(response.headers.get("x-rate-limit-remaining", 0))
                limit = int(response.headers.get("x-rate-limit-limit", 0))
                logger.warning(
                    f"API лимит твитов: {remaining}/{limit}. Сброс в {reset_time}"
                )
                return None

            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                includes = data.get("includes", {})

                if tweets and "media" in includes:
                    media_map = {m["media_key"]: m for m in includes["media"]}

                    for tweet in tweets:
                        if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                            media_keys = tweet["attachments"]["media_keys"]
                            tweet["media"] = []

                            for key in media_keys:
                                if key in media_map:
                                    tweet["media"].append(media_map[key])

                return tweets
            else:
                logger.error(f"Ошибка при получении твитов: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Ошибка запроса к API: {e}")

        return None

    def get_latest_tweet(self, username, last_known_id=None, use_proxies=False):
        """Получает последний твит пользователя через API Twitter"""
        logger.info(f"Запрос твитов для @{username} через API...")

        # Если передан последний известный ID, проверяем нужно ли запрашивать API
        # Используем API только если другие методы нашли более новый твит, но данные о нем неполные
        # Или если другие методы не нашли твит вообще
        if last_known_id:
            # Проверяем кеш API твитов
            cached_data = get_from_cache("tweets", f"api_{username.lower()}", 3600)  # Кеш на 1 час
            if cached_data and "tweet_id" in cached_data:
                cached_id = cached_data["tweet_id"]
                # Если в кеше уже есть этот ID, используем его
                if cached_id == last_known_id:
                    logger.info(f"Найден твит {cached_id} в кеше API для @{username}")
                    return cached_data.get("user_id"), cached_id, cached_data.get("tweet_data")

        # Проверяем, нужно ли вообще обращаться к API
        # (если у нас лимиты исчерпаны или ключа нет - не запрашиваем)
        if not self.bearer_token or not self.check_rate_limit():
            logger.info("API недоступен из-за лимитов или отсутствия ключа")
            return None, None, None

        # Получаем ID пользователя
        user_id = self.get_user_id(username, use_proxies)
        if not user_id:
            logger.warning(f"Не удалось получить ID пользователя @{username}")
            return None, None, None

        # Получаем твиты пользователя
        tweets = self.get_user_tweets(user_id, use_proxies)
        if not tweets:
            logger.warning(f"Не удалось получить твиты для @{username}")
            return user_id, None, None

        try:
            if not isinstance(tweets, list) or len(tweets) == 0:
                logger.warning(f"Получен пустой или неправильный список твитов для @{username}")
                return user_id, None, None

            # Выбираем первый (самый новый) твит
            tweet = tweets[0]
            tweet_id = tweet["id"]
            tweet_text = tweet["text"]
            tweet_created_at = tweet.get("created_at", "")

            # Если нам передан известный ID, проверяем не старше ли полученный твит
            if last_known_id:
                try:
                    # Сравниваем ID
                    if int(tweet_id) <= int(last_known_id):
                        logger.info(f"API вернул более старый или тот же твит ({tweet_id}) для @{username}")
                        # Вернем ID пользователя и известный ID твита, но без данных
                        return user_id, last_known_id, None
                except (ValueError, TypeError):
                    pass

            # Формируем дату в читаемом формате
            formatted_date = ""
            if tweet_created_at:
                try:
                    dt = datetime.fromisoformat(tweet_created_at.replace("Z", "+00:00"))
                    formatted_date = dt.strftime("%d %b %Y, %H:%M")
                except:
                    formatted_date = tweet_created_at

            # Собираем данные о твите
            tweet_data = {
                "text": tweet_text,
                "url": f"https://twitter.com/{username}/status/{tweet_id}",
                "created_at": tweet_created_at,
                "formatted_date": formatted_date,
                "is_pinned": False,
                "has_media": "attachments" in tweet,
                "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0)
            }

            # Обработка медиа-вложений
            if "attachments" in tweet and "media_keys" in tweet["attachments"] and "media" in tweet:
                media = []
                for item in tweet["media"]:
                    media_url = item.get("url", "") or item.get("preview_image_url", "")
                    if media_url:
                        media.append({
                            "type": item.get("type", "photo"),
                            "url": media_url
                        })

                if media:
                    tweet_data["media"] = media

            # Добавляем в кэш
            update_cache("tweets", f"api_{username.lower()}", {
                "user_id": user_id,
                "tweet_id": tweet_id,
                "tweet_data": tweet_data
            })

            logger.info(f"API нашел твит: {tweet_id}")
            return user_id, tweet_id, tweet_data

        except Exception as e:
            logger.error(f"Ошибка при обработке твитов для @{username}: {e}")
            traceback.print_exc()
            return user_id, None, None


class NitterScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Cache-Control": "no-cache"
        })
        # Отключаем проверку SSL для работы со всеми инстансами
        self.session.verify = False
        # Подавляем предупреждения о небезопасных запросах
        import urllib3
        urllib3.disable_warnings()
        self.nitter_failures = {}

    def get_random_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55"
        ]
        return random.choice(agents)

    def report_nitter_failure(self, instance):
        if instance not in self.nitter_failures:
            self.nitter_failures[instance] = 0
        self.nitter_failures[instance] += 1

    def get_healthy_nitter_instances(self, max_failures=3):
        settings = get_settings()
        nitter_instances = settings.get("nitter_instances", NITTER_INSTANCES)

        # Отфильтруем инстансы с большим количеством неудач
        healthy_instances = [
            instance for instance in nitter_instances
            if self.nitter_failures.get(instance, 0) < max_failures
        ]

        # Если все инстансы имеют слишком много неудач, сбросим счетчики и используем все
        if not healthy_instances:
            self.nitter_failures = {}
            healthy_instances = nitter_instances

        # Перемешиваем для равномерной нагрузки
        random.shuffle(healthy_instances)
        return healthy_instances

    def validate_tweet_id(self, username, tweet_id):
        if not tweet_id:
            return False
        if len(str(tweet_id)) < 15:
            logger.warning(f"Слишком короткий ID твита для @{username}: {tweet_id}")
            return False
        return True

    def get_latest_tweet_nitter(self, username, last_known_id=None, use_proxies=False):
        """Получает последний твит через Nitter с проверкой инстансов"""
        logger.info(f"Запрос твитов для @{username} через Nitter...")

        try:
            # Получаем список здоровых инстансов Nitter
            settings = get_settings()
            nitter_instances = settings.get("nitter_instances", NITTER_INSTANCES)

            if not nitter_instances:
                logger.error("Нет доступных Nitter-инстансов")
                return None, None

            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }

            # Перебираем инстансы в случайном порядке
            random.shuffle(nitter_instances)

            newest_tweet_id = None
            newest_tweet_data = None
            newest_timestamp = None

            # Пробуем разные инстансы Nitter
            for nitter in nitter_instances[:3]:
                try:
                    # Добавляем случайное число для обхода кеширования
                    cache_buster = f"?r={int(time.time())}"
                    full_url = f"{nitter}/{username}{cache_buster}"

                    logger.info(f"Попытка получения твитов через {nitter}...")

                    proxies = get_random_proxy() if use_proxies else None
                    nitter_response = self.session.get(full_url, headers=headers, proxies=proxies, timeout=15)

                    if nitter_response.status_code != 200:
                        logger.warning(f"Nitter {nitter} вернул код {nitter_response.status_code}")
                        self.report_nitter_failure(nitter)
                        continue

                    soup = BeautifulSoup(nitter_response.text, 'html.parser')

                    # Поиск всех твитов
                    tweet_divs = soup.select('.timeline-item')

                    if not tweet_divs:
                        logger.warning(f"Не найдены твиты на {nitter} для @{username}")
                        self.report_nitter_failure(nitter)
                        continue

                    logger.info(f"Найдено {len(tweet_divs)} твитов на {nitter}")

                    # Проходим по всем найденным твитам
                    for tweet_div in tweet_divs:
                        # Проверяем на закрепленный твит
                        is_pinned = bool(tweet_div.select_one('.pinned'))

                        # Проверяем на ретвит
                        is_retweet = bool(tweet_div.select_one('.retweet-header'))

                        # Пропускаем закрепленные твиты и ретвиты если есть последний известный ID
                        if last_known_id and (is_pinned or is_retweet):
                            continue

                        # Извлекаем дату твита
                        tweet_date = tweet_div.select_one('.tweet-date a')
                        if not tweet_date or not tweet_date.get('title'):
                            continue

                        # Формат даты в Nitter: "Mar 28, 2025 · 10:50 PM UTC"
                        date_str = tweet_date.get('title')
                        display_date = date_str

                        try:
                            # Пробуем разные форматы дат
                            date_formats = [
                                '%b %d, %Y · %I:%M %p UTC',  # Mar 28, 2025 · 10:50 PM UTC
                                '%d %b %Y · %H:%M:%S UTC',  # 28 Mar 2025 · 22:50:00 UTC
                                '%B %d, %Y · %I:%M %p UTC',  # March 28, 2025 · 10:50 PM UTC
                                '%Y-%m-%d %H:%M:%S'  # 2025-03-28 22:50:09
                            ]

                            tweet_datetime = None
                            for fmt in date_formats:
                                try:
                                    tweet_datetime = datetime.strptime(date_str, fmt)
                                    break
                                except:
                                    continue

                            if not tweet_datetime:
                                # Если не удалось распознать дату, пропускаем твит
                                continue

                            tweet_timestamp = tweet_datetime.timestamp()
                        except Exception as e:
                            continue

                        # Ссылка на твит и извлечение ID
                        tweet_link = tweet_div.select_one('.tweet-link')
                        if not tweet_link or not tweet_link.get('href'):
                            continue

                        # Путь к твиту типа /username/status/12345678
                        href = tweet_link.get('href')
                        # Извлекаем ID
                        match = re.search(r'/status/(\d+)', href)
                        if not match:
                            continue

                        tweet_id = match.group(1)

                        # Если передан последний известный ID, проверяем, новее ли текущий
                        if last_known_id:
                            try:
                                if int(tweet_id) <= int(last_known_id):
                                    logger.info(
                                        f"Nitter: твит {tweet_id} не новее последнего известного {last_known_id}")
                                    continue  # Пропускаем этот твит, ищем более новые
                            except (ValueError, TypeError):
                                # При ошибке сравнения проверяем по времени
                                pass

                        # Проверяем, является ли этот твит новее найденного ранее
                        if newest_timestamp is None or tweet_timestamp > newest_timestamp:
                            newest_timestamp = tweet_timestamp
                            newest_tweet_id = tweet_id

                            # Текст твита
                            tweet_content = tweet_div.select_one('.tweet-content')
                            tweet_text = tweet_content.get_text() if tweet_content else "[Текст недоступен]"

                            # URL твита
                            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

                            # Проверяем наличие медиа
                            has_images = bool(tweet_div.select('.attachments .attachment-image'))
                            has_video = bool(tweet_div.select('.attachments .attachment-video'))

                            # Получаем метрики, если доступны
                            stats = tweet_div.select('.tweet-stats .icon-container')
                            likes = 0
                            retweets = 0

                            for stat in stats:
                                stat_text = stat.get_text(strip=True)
                                if "retweet" in stat.get('class', []):
                                    try:
                                        retweets = int(stat_text)
                                    except:
                                        pass
                                elif "heart" in stat.get('class', []):
                                    try:
                                        likes = int(stat_text)
                                    except:
                                        pass

                            # Собираем медиа ссылки
                            media = []
                            if has_images:
                                for img in tweet_div.select('.attachments .attachment-image img'):
                                    if img.get('src'):
                                        media.append({
                                            "type": "photo",
                                            "url": img['src']
                                        })

                            if has_video:
                                for video in tweet_div.select('.attachments .attachment-video source'):
                                    if video.get('src'):
                                        media.append({
                                            "type": "video",
                                            "url": video['src']
                                        })

                            # Данные о твите
                            newest_tweet_data = {
                                "text": tweet_text,
                                "url": tweet_url,
                                "is_pinned": is_pinned,
                                "is_retweet": is_retweet,
                                "created_at": str(tweet_datetime) if tweet_datetime else "",
                                "formatted_date": display_date,
                                "timestamp": tweet_timestamp,
                                "has_media": has_images or has_video,
                                "likes": likes,
                                "retweets": retweets,
                                "media": media if (has_images or has_video) else []
                            }

                            logger.info(f"Найден твит от {display_date}, ID: {tweet_id}")

                    # Если нашли хотя бы один твит, останавливаемся
                    if newest_tweet_id:
                        break

                except Exception as e:
                    logger.error(f"Ошибка при обращении к {nitter}: {e}")
                    self.report_nitter_failure(nitter)
                    continue

            # Если нашли хотя бы один твит
            if newest_tweet_id and self.validate_tweet_id(username, newest_tweet_id):
                logger.info(f"Самый новый твит (ID: {newest_tweet_id}) от {newest_tweet_data.get('formatted_date')}")

                # Сохраняем в кеш с принудительной очисткой старых данных
                update_cache("tweets", f"nitter_{username.lower()}", {
                    "tweet_id": newest_tweet_id,
                    "tweet_data": newest_tweet_data,
                    "updated_at": time.time()
                }, force=True)

                return newest_tweet_id, newest_tweet_data

            logger.warning(f"Не удалось найти твиты для @{username} через все доступные серверы Nitter")

        except Exception as e:
            logger.error(f"Общая ошибка при получении твитов для @{username} через Nitter: {e}")
            traceback.print_exc()

        return None, None


class WebScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0"
        ]

    def get_random_user_agent(self):
        return random.choice(self.user_agents)

    def validate_tweet_id(self, username, tweet_id):
        if not tweet_id:
            return False
        if len(str(tweet_id)) < 15:
            logger.warning(f"Слишком короткий ID твита для @{username}: {tweet_id}")
            return False
        return True

    def get_latest_tweet_web(self, username, last_known_id=None, use_proxies=False, max_retries=2):
        """Веб-скрапинг Twitter с использованием существующего Safari"""
        logger.info(f"Запрос твитов для @{username} через веб-скрапинг...")

        # Проверяем кеш если есть последний ID
        if last_known_id:
            cached_data = get_from_cache("tweets", f"web_{username.lower()}", 3600)
            if cached_data and cached_data.get("tweet_id") == last_known_id:
                logger.info(f"Найден твит {last_known_id} в кеше для @{username}, пропускаем веб-скрапинг")
                return last_known_id, cached_data.get("tweet_data")

        retry_count = 0
        while retry_count < max_retries:
            logger.info(f"Попытка {retry_count + 1}/{max_retries} через Safari")

            try:
                # Используем Safari для скрапинга через AppleScript
                with SafariBrowser() as browser:
                    # URL для страницы со свежими твитами
                    url = f"https://twitter.com/{username}"

                    logger.info(f"Загрузка страницы {url} через Safari")
                    browser.get(url)

                    # Даем время для полной загрузки
                    time.sleep(5)

                    # Скроллинг для загрузки контента
                    browser.execute_script("window.scrollBy(0, 500);")
                    time.sleep(3)

                    # Собираем данные о твитах с помощью JavaScript
                    tweets_data = session.driver.execute_script("""
                        const tweets = [];
                        try {
                            const articleElements = document.querySelectorAll('article[data-testid="tweet"]');
                            console.log('Найдено твитов: ' + articleElements.length);

                            for (const article of articleElements) {
                                // Ищем ID твита
                                const links = article.querySelectorAll('a');
                                let tweetId = null;

                                for (const link of links) {
                                    if (link.href && link.href.includes('/status/')) {
                                        const match = link.href.match(/\\/status\\/([0-9]+)/);  // Исправлено экранирование
                                        if (match) {
                                            tweetId = match[1];
                                            break;
                                        }
                                    }
                                }

                                if (!tweetId) continue;

                                // Ищем текст твита
                                const textEl = article.querySelector('[data-testid="tweetText"]');
                                const tweetText = textEl ? textEl.innerText : '';

                                // Ищем дату
                                const timeEl = article.querySelector('time');
                                const displayDate = timeEl ? timeEl.innerText : '';
                                const timestamp = timeEl ? timeEl.getAttribute('datetime') : '';

                                // Проверяем закрепленный ли твит
                                const headerEls = article.querySelectorAll('[dir="auto"]');
                                let isPinned = false;
                                for (const header of headerEls) {
                                    if (header.textContent && 
                                        (header.textContent.includes('Pinned') || 
                                         header.textContent.includes('Закрепленный'))) {
                                        isPinned = true;
                                        break;
                                    }
                                }

                                tweets.push({
                                    id: tweetId,
                                    text: tweetText,
                                    displayDate: displayDate,
                                    timestamp: timestamp,
                                    isPinned: isPinned
                                });
                            }
                        } catch(e) {
                            console.error("Ошибка: " + e.message);
                        }
                        return tweets;
                    """)

                    result = browser.execute_script(js_code)

                    if not result:
                        logger.warning(f"Не удалось получить твиты для @{username}")
                        retry_count += 1
                        continue

                    try:
                        tweets_data = json.loads(result)
                        logger.info(f"Извлечено {len(tweets_data)} твитов для @{username}")
                    except:
                        logger.warning(f"Не удалось распарсить результат от Safari")
                        retry_count += 1
                        continue


                    if tweets_data and len(tweets_data) > 0:
                        # Отфильтровываем закрепленные твиты если ищем обновления
                        if last_known_id:
                            regular_tweets = [t for t in tweets_data if not t.get('isPinned')]
                            target_tweets = regular_tweets or tweets_data
                        else:
                            target_tweets = tweets_data

                        # Сортируем по ID (самые новые в начале)
                        try:
                            target_tweets.sort(key=lambda x: int(x.get('id', '0')), reverse=True)
                        except:
                            pass

                        if target_tweets:
                            selected_tweet = target_tweets[0]
                            tweet_id = selected_tweet.get('id')

                            # Проверяем, новее ли найденный твит последнего известного
                            if last_known_id:
                                try:
                                    is_newer = int(tweet_id) > int(last_known_id)
                                    if not is_newer:
                                        # Если не нашли более новый твит, возвращаем последний известный
                                        logger.warning(
                                            f"Web через Safari не нашел новый твит для @{username} (текущий: {last_known_id})")
                                        return last_known_id, cached_data.get("tweet_data") if cached_data else None
                                except (ValueError, TypeError):
                                    pass

                            if not self.validate_tweet_id(username, tweet_id):
                                logger.warning(f"Некорректный ID твита: {tweet_id}")
                                retry_count += 1
                                continue

                            # Формируем данные о твите
                            tweet_data = {
                                "text": selected_tweet.get('text', '[Текст недоступен]'),
                                "url": f"https://twitter.com/{username}/status/{tweet_id}",
                                "created_at": selected_tweet.get('timestamp', ''),
                                "formatted_date": selected_tweet.get('displayDate', 'неизвестная дата'),
                                "is_pinned": selected_tweet.get('isPinned', False),
                                "has_media": selected_tweet.get('hasMedia', False),
                                "media": selected_tweet.get('media', []),
                                "browser_used": "Safari"
                            }

                            # Обновляем кеш
                            update_cache("tweets", f"web_{username.lower()}", {
                                "tweet_id": tweet_id,
                                "tweet_data": tweet_data
                            })

                            logger.info(f"Найден твит ID {tweet_id} для @{username} через Safari")
                            return tweet_id, tweet_data

                    # Если не нашли твиты, попробуем снова
                    retry_count += 1

            except Exception as e:
                retry_count += 1
                logger.error(f"Ошибка при получении твитов для @{username} через Safari: {e}")
                time.sleep(random.uniform(1.5, 3))  # Случайная пауза перед повторной попыткой

        return None, None


async def cmd_auth_google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает автоматическую авторизацию в Twitter через Google"""
    message = update.effective_message
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await message.reply_text("⛔️ У вас нет доступа к этой команде.")
        return

    # Проверка наличия учетных данных
    if not context.bot_data.get('google_email') or not context.bot_data.get('google_password'):
        await message.reply_text(
            "Необходимо сначала установить учетные данные Google.\n\n"
            "Используйте команду: /set_google_credentials email password"
        )
        return

    status_msg = await message.reply_text(
        "🔄 Запускаю полностью автоматическую авторизацию в Twitter через Google...\n\n"
        "⚠️ ВАЖНО: Когда откроется Safari WebDriver:\n"
        "1. Нажмите 'Continue Session' в диалоговом окне\n"
        "2. Дальше бот всё сделает автоматически\n"
        "3. Подождите завершения процесса авторизации"
    )

    email = context.bot_data.get('google_email')
    password = context.bot_data.get('google_password')

    # Запускаем авторизацию в отдельном потоке
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(twitter_login_with_google, email, password)

        try:
            # Ждем завершения с таймаутом
            success = future.result(timeout=60)

            if success:
                await status_msg.edit_text(
                    "✅ Успешная авторизация в Twitter через Google!\n\n"
                    "Теперь бот будет использовать эту сессию для скрапинга."
                )
            else:
                await status_msg.edit_text(
                    "❌ Не удалось выполнить автоматическую авторизацию.\n\n"
                    "Проверьте журнал ошибок и учетные данные Google."
                )
        except Exception as e:
            await status_msg.edit_text(
                f"❌ Ошибка при авторизации: {str(e)}\n\n"
                "Возможно, потребуется ручное вмешательство."
            )

async def cmd_set_google_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает учетные данные Google для автоматического входа"""
    message = update.effective_message
    user_id = update.effective_user.id

    # Проверка прав администратора
    if not is_admin(user_id):
        await message.reply_text("⛔️ У вас нет доступа к этой команде.")
        return

    # Проверяем, что предоставлены параметры
    if len(context.args) < 2:
        await message.reply_text(
            "⚠️ Пожалуйста, укажите email и пароль.\n"
            "Пример: /set_google_credentials your.email@gmail.com your_password"
        )
        return

    # Получаем email и пароль
    email = context.args[0]
    password = context.args[1]

    # Сохраняем учетные данные в bot_data
    context.bot_data['google_email'] = email
    context.bot_data['google_password'] = password

    # Удаляем сообщение с паролем для безопасности
    try:
        await message.delete()
    except:
        pass

    # Отправляем подтверждение
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Учетные данные Google установлены для email: {email}"
    )


async def cmd_auth_google_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простой вариант входа через Google с обычным Safari"""
    message = update.effective_message
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await message.reply_text("⛔️ У вас нет доступа к этой команде.")
        return

    status_msg = await message.reply_text(
        "🔄 Запускаю Safari для входа через Google...\n\n"
        "⚠️ Дальше вам нужно будет:\n"
        "1. Выбрать свой Google аккаунт\n"
        "2. Подтвердить вход\n"
        "3. Нажать кнопку ниже, когда авторизация будет завершена"
    )

    # Запускаем Safari
    success = login_with_regular_safari()

    if success:
        # Добавляем кнопку для подтверждения
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Я вошел в Twitter", callback_data="auth_completed")
        ]])

        await status_msg.edit_text(
            "✅ Safari запущен, кнопка Google нажата!\n\n"
            "Теперь:\n"
            "1. Выберите свой Google аккаунт\n"
            "2. Завершите процесс авторизации\n"
            "3. Нажмите кнопку ниже, когда войдете в Twitter",
            reply_markup=keyboard
        )
    else:
        await status_msg.edit_text(
            "❌ Не удалось автоматически нажать на кнопку Google.\n"
            "Пожалуйста, нажмите на нее вручную и завершите вход."
        )

async def send_tweet_with_media(app, subs, username, tweet_id, tweet_data):
    # Формируем сообщение
    tweet_text = tweet_data.get('text', '[Новый твит]')
    tweet_url = tweet_data.get('url', f"https://twitter.com/{username}/status/{tweet_id}")
    formatted_date = tweet_data.get('formatted_date', '')

    likes = tweet_data.get('likes', 0)
    retweets = tweet_data.get('retweets', 0)
    browser_used = tweet_data.get('browser_used', '')

    # Формируем метрики
    metrics_text = f"👍 {likes} · 🔄 {retweets}" if likes or retweets else ""
    if browser_used:
        metrics_text += f" · 🌐 {browser_used}" if metrics_text else f"🌐 {browser_used}"

    # Основное сообщение
    tweet_msg = f"🐦 @{username}"

    # Добавляем дату
    if formatted_date:
        tweet_msg += f" · {formatted_date}"

    # Добавляем текст
    tweet_msg += f"\n\n{tweet_text}"

    # URL и метрики
    footer = f"\n\n{tweet_url}"
    if metrics_text:
        footer += f"\n\n{metrics_text}"

    # Проверяем наличие медиа
    media = tweet_data.get('media', [])
    has_media = tweet_data.get('has_media', False) or len(media) > 0

    # Если subs - это просто ID чата (не список), преобразуем в список
    if not isinstance(subs, list):
        subs = [subs]

    for chat_id in subs:
        try:
            # Если нет медиа, отправляем обычное сообщение
            if not has_media:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=tweet_msg + footer,
                    disable_web_page_preview=False
                )
                continue

            # Ищем URL фотографий
            photo_urls = []
            for item in media:
                if isinstance(item, dict) and 'type' in item and item.get('type',
                                                                          '').lower() == 'photo' and 'url' in item:
                    photo_urls.append(item['url'])

                # Если нашли фото
                if photo_urls:
                    # Ограничение длины подписи в Telegram
                    caption = (tweet_msg + footer)[:1024]

                    # Отправляем первое фото с подписью
                    await app.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_urls[0],
                        caption=caption
                    )

                    # Если есть дополнительные фото, отправляем их отдельно
                    for url in photo_urls[1:]:
                        try:
                            await app.bot.send_photo(
                                chat_id=chat_id,
                                photo=url
                            )
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Ошибка при отправке дополнительного фото: {e}")
                else:
                    # Если фото не нашли, отправляем обычное сообщение с превью
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=tweet_msg + footer,
                        disable_web_page_preview=False
                    )

                await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями

        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}")
            # В случае ошибки отправляем текстовое сообщение
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=tweet_msg + footer,
                    disable_web_page_preview=False
                )
            except:
                pass


async def check_tweet_multi_method(username, account_methods=None, use_proxies=False, max_retries=2):
    """Проверяет твиты всеми доступными методами с учетом индивидуальных настроек аккаунта и порядком приоритета"""
    # Получаем настройки методов
    settings = get_settings()
    accounts = init_accounts()
    account = accounts.get(username.lower(), {})
    last_known_id = account.get('last_tweet_id')

    # Определяем какие методы использовать
    if account_methods:
        methods = account_methods
    elif account.get("scraper_methods"):
        methods = account["scraper_methods"]
        logger.info(f"Используем индивидуальные методы для @{username}: {methods}")
    else:
        methods = settings.get("scraper_methods", ["nitter", "web", "api"])
        logger.info(f"Используем общие методы скрапинга: {methods}")

    twitter_client = TwitterClient(TWITTER_BEARER)
    nitter_scraper = NitterScraper()
    web_scraper = WebScraper()

    results = {
        "api": {"user_id": None, "tweet_id": None, "tweet_data": None},
        "nitter": {"tweet_id": None, "tweet_data": None},
        "web": {"tweet_id": None, "tweet_data": None}
    }

    found_new_id = False  # Флаг, определяющий нашли ли мы новый ID

    # Проверяем методы в указанном порядке
    for method in methods:
        try:
            # Если мы уже нашли новый твит, прерываем дальнейший поиск
            if found_new_id:
                logger.info(
                    f"Уже нашли новый твит методом {next(k for k, v in results.items() if v.get('tweet_id'))}, пропускаем остальные методы")
                break

            if method == "nitter":
                tweet_id, tweet_data = nitter_scraper.get_latest_tweet_nitter(username, last_known_id, use_proxies)
                if tweet_id:
                    results["nitter"]["tweet_id"] = tweet_id
                    results["nitter"]["tweet_data"] = tweet_data
                    logger.info(f"Nitter нашел твит: {tweet_id}")
                    if last_known_id and int(tweet_id) > int(last_known_id):
                        found_new_id = True

            elif method == "api" and TWITTER_BEARER and not twitter_client.rate_limited:
                user_id, tweet_id, tweet_data = twitter_client.get_latest_tweet(username, last_known_id, use_proxies)
                if user_id:
                    results["api"]["user_id"] = user_id
                if tweet_id:
                    results["api"]["tweet_id"] = tweet_id
                    results["api"]["tweet_data"] = tweet_data
                    logger.info(f"API нашел твит: {tweet_id}")
                    if last_known_id and int(tweet_id) > int(last_known_id):
                        found_new_id = True

            elif method == "web":
                # Используем только Safari для веб-скрапинга
                tweet_id, tweet_data = web_scraper.get_latest_tweet_web(username, last_known_id, use_proxies,
                                                                        max_retries)
                if tweet_id:
                    results["web"]["tweet_id"] = tweet_id
                    results["web"]["tweet_data"] = tweet_data
                    logger.info(f"Web нашел твит: {tweet_id}")
                    if last_known_id and int(tweet_id) > int(last_known_id):
                        found_new_id = True

        except Exception as e:
            logger.error(f"Ошибка при проверке {username} методом {method}: {e}")
            traceback.print_exc()

    # Собираем все найденные ID твитов
    tweet_ids = {}
    for method, data in results.items():
        if data["tweet_id"]:
            tweet_ids[method] = data["tweet_id"]

    logger.info(f"Найденные ID для @{username}: {tweet_ids}")

    # Если ничего не нашли
    if not tweet_ids:
        return None, None, None, None

    # Выбираем самый большой ID (самый новый твит)
    try:
        newest_method, newest_id = max(tweet_ids.items(), key=lambda x: int(x[1]))
        logger.info(f"Выбран самый новый твит: {newest_id} (метод: {newest_method})")
    except (ValueError, TypeError):
        # При ошибке берем первый найденный
        newest_method = next(iter(tweet_ids))
        newest_id = tweet_ids[newest_method]
        logger.warning(f"Не удалось сравнить ID твитов, выбран первый: {newest_id}")

    # Получаем user_id из API (если был найден)
    user_id = results["api"]["user_id"]
    # Получаем данные твита от выбранного метода
    tweet_data = results[newest_method]["tweet_data"]

    # Если данных нет, но есть твит - попробуем данные из другого метода
    if newest_id and not tweet_data:
        for method, data in results.items():
            if data["tweet_id"] == newest_id and data["tweet_data"]:
                tweet_data = data["tweet_data"]
                break

    return user_id, newest_id, tweet_data, newest_method


async def process_account(app, subs, accounts, username, account, methods, use_proxies):
    """Обрабатывает один аккаунт и отправляет уведомления при новых твитах"""
    try:
        # Обновляем время проверки
        account['last_check'] = datetime.now().isoformat()
        account['check_count'] = account.get('check_count', 0) + 1

        # Получаем последний известный твит и проверяем флаг первой проверки
        last_id = account.get('last_tweet_id')
        first_check = account.get('first_check', False)

        # Проверяем флаг приватности аккаунта
        is_private = account.get('is_private', False)

        logger.info(f"Проверка аккаунта @{username}, последний ID: {last_id}" +
                    (", приватный: да" if is_private else ""))

        # Используем мультиметодную проверку с учетом приватности
        user_id, tweet_id, tweet_data, method = await check_tweet_multi_method(
            username, methods, use_proxies
        )

        # Обновляем ID пользователя, если получили новый
        if user_id and not account.get('user_id'):
            account['user_id'] = user_id

        # Если не нашли твит
        if not tweet_id:
            # Увеличиваем счетчик неудач
            account['fail_count'] = account.get('fail_count', 0) + 1
            total_checks = account.get('check_count', 1)
            fail_count = account.get('fail_count', 0)
            account['success_rate'] = 100 * (total_checks - fail_count) / total_checks
            # Уменьшаем приоритет проблемных аккаунтов
            if account.get('fail_count', 0) > 3:
                account['priority'] = max(0.1, account.get('priority', 1.0) * 0.9)
            return True

        # Сбрасываем счетчик неудач при успехе
        if account.get('fail_count', 0) > 0:
            account['fail_count'] = max(0, account.get('fail_count', 0) - 1)

        # Обновляем процент успеха
        total_checks = account.get('check_count', 1)
        fail_count = account.get('fail_count', 0)
        account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

        # Обновляем метод проверки
        account['check_method'] = method

        # Сравниваем найденный ID с последним известным
        if last_id and not first_check:
            try:
                if int(tweet_id) <= int(last_id):
                    logger.warning(f"⚠️ Аккаунт @{username}: найден более старый твит {tweet_id} " +
                                   f"(текущий {last_id}), игнорируем!")
                    return True
            except (ValueError, TypeError):
                logger.warning(f"Не удалось сравнить ID твитов для @{username}")

        # Если это первая проверка или найден более новый твит
        if first_check or tweet_id != last_id:
            # Обновляем данные твита
            account['check_method'] = method
            if tweet_data:
                account['last_tweet_text'] = tweet_data.get('text', '')
                account['last_tweet_url'] = tweet_data.get('url', '')
                account['tweet_data'] = tweet_data

            if first_check:
                account['first_check'] = False
                account['last_tweet_id'] = tweet_id
                logger.info(f"Аккаунт @{username}: первая проверка, сохранен ID {tweet_id}")
                return True
            else:
                # Нашли новый твит
                account['last_tweet_id'] = tweet_id
                logger.info(f"Аккаунт @{username}: новый твит {tweet_id}, отправляем уведомления")

                # Отправляем уведомления
                if tweet_data:
                    await send_tweet_with_media(app, subs, username, tweet_id, tweet_data)
                return True
        else:
            # ID совпадает, нет новых твитов
            logger.info(f"Аккаунт @{username}: нет новых твитов (метод: {method})")
            return False

    except Exception as e:
        logger.error(f"Ошибка при обработке аккаунта @{username}: {e}")
        traceback.print_exc()

        # Увеличиваем счетчик неудач
        account['fail_count'] = account.get('fail_count', 0) + 1

        # Обновляем процент успеха
        total_checks = account.get('check_count', 1)
        fail_count = account.get('fail_count', 0)
        account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

        # Уменьшаем приоритет проблемных аккаунтов
        if account.get('fail_count', 0) > 3:
            account['priority'] = max(0.1, account.get('priority', 1.0) * 0.9)

    return True


async def on_startup(app):
    """Вызывается при запуске бота"""
    logger.info("Бот запущен, инициализация...")

    # Инициализируем команды бота
    await app.bot.set_my_commands([
        BotCommand("start", "Начало работы"),
        BotCommand("add", "Добавить аккаунт"),
        BotCommand("remove", "Удалить аккаунт"),
        BotCommand("list", "Список аккаунтов"),
        BotCommand("check", "Проверить аккаунты"),
        BotCommand("settings", "Настройки бота"),
        BotCommand("methods", "Настройка методов скрапинга"),
        BotCommand("update_nitter", "Обновить Nitter-инстансы"),
        BotCommand("auth", "Запустить Safari для авторизации"),
        BotCommand("stats", "Статистика веб-скрапинга"),
        BotCommand("reset", "Сброс данных аккаунта"),
        BotCommand("set_google_credentials", "Установка учетных данных Google"),
        BotCommand("auth_google", "Запуск авторизацию через Google:"),
        BotCommand("auth_google_simple", "Запуск авторизацию обычную через Google:"),
    ])

    # Инициализируем данные
    init_accounts()

    # Создаем файл прокси, если не существует
    if not os.path.exists(PROXIES_FILE):
        save_json(PROXIES_FILE, {"proxies": []})

    # Создаем файл кеша, если не существует
    if not os.path.exists(CACHE_FILE):
        save_json(CACHE_FILE, {"tweets": {}, "users": {}, "timestamp": int(time.time())})

    # Создаем файл статистики браузеров, если не существует
    if not os.path.exists(BROWSER_STATS_FILE):
        save_json(BROWSER_STATS_FILE, {"browsers": {}, "last_update": int(time.time())})

    # Обновляем список Nitter-инстансов
    try:
        logger.info("Обновление списка Nitter-инстансов...")
        asyncio.create_task(update_nitter_instances())
    except Exception as e:
        logger.error(f"Ошибка при обновлении Nitter-инстансов: {e}")

    # Запускаем фоновую задачу проверки твитов
    global background_task
    background_task = asyncio.create_task(background_check(app))
    logger.info("Фоновая задача активирована")


async def on_shutdown(app):
    """Вызывается при остановке бота"""
    global background_task, safari_driver

    if background_task and not background_task.done() and not background_task.cancelled():
        logger.info("Останавливаем фоновую задачу...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка при остановке фоновой задачи: {e}")
        logger.info("Фоновая задача остановлена")

    # Закрываем Safari WebDriver при завершении работы
    if safari_driver is not None:
        try:
            # НЕ ЗАКРЫВАЕМ safari_driver.quit() - это закроет окно!
            # Просто логируем
            logger.info("Safari WebDriver существует при завершении")
        except:
            pass

# Глобальная переменная для фоновой задачи
background_task = None


async def background_check(app):
    """Фоновая проверка аккаунтов с улучшенной логикой приоритетов"""
    global background_task
    background_task = asyncio.current_task()

    # При запуске не проверяем сразу, ждем интервал
    settings = get_settings()
    wait_time = settings.get("check_interval", DEFAULT_CHECK_INTERVAL)
    logger.info(f"Фоновая задача запущена, проверка через {wait_time} секунд")
    await asyncio.sleep(wait_time)

    while True:
        try:
            # Проверка на отмену задачи
            if asyncio.current_task().cancelled():
                logger.info("Фоновая задача отменена")
                break

            settings = get_settings()
            if not settings.get("enabled", True):
                logger.info("Мониторинг отключен, пропускаем проверку")
                await asyncio.sleep(settings["check_interval"])
                continue

            logger.info("Фоновая проверка аккаунтов")
            subs = load_json(SUBSCRIBERS_FILE, [])
            accounts = init_accounts()

            # Пропускаем проверку, если нет подписчиков или аккаунтов
            if not subs or not accounts:
                logger.info("Нет подписчиков или аккаунтов, пропускаем проверку")
                await asyncio.sleep(settings["check_interval"])
                continue

            # Получаем настройки
            use_proxies = settings.get("use_proxies", False)
            methods = settings.get("scraper_methods", ["nitter", "web", "api"])
            parallel_checks = settings.get("parallel_checks", 3)
            randomize = settings.get("randomize_intervals", True)
            accounts_updated = False

            # Проверяем, нужно ли обновить инстансы Nitter
            if "nitter" in methods:
                current_time = int(time.time())
                last_check = settings.get("last_health_check", 0)
                health_check_interval = settings.get("health_check_interval", 1800)  # 30 минут

                if current_time - last_check > health_check_interval:
                    logger.info("Обновление списка Nitter-инстансов...")
                    try:
                        await update_nitter_instances()
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении Nitter-инстансов: {e}")

            # Улучшенная сортировка аккаунтов с учетом приоритета и времени
            now = datetime.now()
            sorted_accounts = []

            for username, account in accounts.items():
                # Пропускаем аккаунты с отключенными методами
                if account.get("scraper_methods") == []:
                    logger.info(f"Пропускаем аккаунт @{username} с пустым списком методов")
                    continue

                # Базовый приоритет
                priority = account.get("priority", 1.0)

                # Увеличиваем приоритет для аккаунтов с высоким процентом неудач
                fail_count = account.get("fail_count", 0)
                if fail_count > 0:
                    priority += min(0.5, fail_count * 0.1)

                # Уменьшаем приоритет для недавно проверенных аккаунтов
                last_check = account.get("last_check", "2000-01-01T00:00:00")
                try:
                    last_check_dt = datetime.fromisoformat(last_check)
                    hours_since_check = (now - last_check_dt).total_seconds() / 3600

                    # Если проверяли менее 1 часа назад, уменьшаем приоритет
                    if hours_since_check < 1:
                        priority -= 0.5 * (1 - hours_since_check)  # От -0 до -0.5
                except Exception:
                    pass

                sorted_accounts.append((username, account, priority))

            # Сортируем по уменьшению приоритета
            sorted_accounts.sort(key=lambda x: x[2], reverse=True)

            # Проверяем аккаунты группами для параллельной обработки
            for i in range(0, len(sorted_accounts), parallel_checks):
                # Если задача отменена, выходим
                if asyncio.current_task().cancelled():
                    logger.info("Фоновая задача отменена")
                    return

                # Берем очередную группу аккаунтов
                batch = sorted_accounts[i:i + parallel_checks]
                tasks = []

                # Создаем задачи для параллельной проверки аккаунтов
                for username, account, _ in batch:
                    if asyncio.current_task().cancelled():
                        break

                    display_name = account.get('username', username)
                    account_methods = account.get('scraper_methods', methods)
                    tasks.append(
                        process_account(app, subs, accounts, display_name, account, account_methods, use_proxies))

                # Запускаем все задачи параллельно
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Ошибка в параллельной проверке: {result}")
                        elif result:  # Если был обновлен аккаунт
                            accounts_updated = True

                # Небольшая задержка между группами
                await asyncio.sleep(2)

            # Сохраняем обновленные данные
            if accounts_updated:
                save_accounts(accounts)

            # Определяем время до следующей проверки
            if randomize:
                # Случайное время в пределах диапазона
                min_factor = settings.get("min_interval_factor", 0.8)
                max_factor = settings.get("max_interval_factor", 1.2)
                factor = random.uniform(min_factor, max_factor)
                wait_time = int(settings["check_interval"] * factor)
                logger.info(f"Случайное время ожидания: {wait_time} секунд (x{factor:.2f})")
            else:
                wait_time = settings["check_interval"]
                logger.info(f"Следующая проверка через {wait_time} секунд")

            await asyncio.sleep(wait_time)

        except asyncio.CancelledError:
            logger.info("Фоновая задача отменена")
            break
        except Exception as e:
            logger.error(f"Ошибка в фоновой проверке: {e}")
            traceback.print_exc()
            # Не останавливаем задачу при ошибках
            await asyncio.sleep(60)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id
    subs = load_json(SUBSCRIBERS_FILE, [])
    if chat_id not in subs:
        subs.append(chat_id)
        save_json(SUBSCRIBERS_FILE, subs)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")],
        [InlineKeyboardButton("🔍 Проверить аккаунты", callback_data="check")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

    await update.message.reply_text(
        "👋 Бот мониторинга Twitter!\n\n"
        "Используйте команды:\n"
        "/add <username> - добавить аккаунт\n"
        "/remove <username> - удалить аккаунт\n"
        "/list - список аккаунтов\n"
        "/check - показать последние твиты\n"
        "/settings - настройки\n"
        "/methods <username> - приоритет проверок\n"
        "/reset <username> - сброс данных аккаунта\n"
        "/stats - статистика браузеров\n"
        "/update_nitter - обновляет список Nitter-инстансы\n"
        "/auth - запустить Safari для авторизации\n\n"
        "Бот автоматически проверяет новые твиты и отправляет уведомления.",
        reply_markup=keyboard
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет новый аккаунт для отслеживания"""
    if not context.args:
        return await update.message.reply_text("Использование: /add <username>")

    username = context.args[0].lstrip("@")
    accounts = init_accounts()

    if username.lower() in accounts:
        return await update.message.reply_text(
            f"@{username} уже добавлен.\nИспользуйте /settings для управления аккаунтом.")

    message = await update.message.reply_text(f"Проверяем @{username}...")

    settings = get_settings()
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    user_id, tweet_id, tweet_data, method = await check_tweet_multi_method(
        username, methods, use_proxies
    )

    if not tweet_id:
        return await message.edit_text(f"❌ Не удалось найти аккаунт @{username} или получить его твиты.")

    accounts[username.lower()] = {
        "username": username,
        "user_id": user_id,
        "added_at": datetime.now().isoformat(),
        "last_check": datetime.now().isoformat(),
        "last_tweet_id": tweet_id,
        "check_count": 1,
        "success_rate": 100.0,
        "fail_count": 0,
        "check_method": method,
        "priority": 1.0,
        "first_check": True,
        "last_tweet_text": tweet_data.get('text', '[Текст недоступен]') if tweet_data else '[Текст недоступен]',
        "last_tweet_url": tweet_data.get('url',
                                         f"https://twitter.com/{username}/status/{tweet_id}") if tweet_data else f"https://twitter.com/{username}/status/{tweet_id}",
        "tweet_data": tweet_data or {},
        "scraper_methods": None
    }
    save_accounts(accounts)

    # Создаем подробное сообщение с информацией о твите
    if tweet_data:
        tweet_text = tweet_data.get('text', '[Текст недоступен]')
        tweet_url = tweet_data.get('url', f"https://twitter.com/{username}/status/{tweet_id}")
        formatted_date = tweet_data.get('formatted_date', '')

        likes = tweet_data.get('likes', 0)
        retweets = tweet_data.get('retweets', 0)

        result = f"✅ Добавлен @{username}\n\n"

        if formatted_date:
            result += f"📅 Дата: {formatted_date}\n"

        result += f"📝 Последний твит:\n{tweet_text}\n\n"
        result += f"🆔 ID твита: {tweet_id}\n"
        result += f"🔍 Метод проверки: {method}\n"

        if likes or retweets:
            result += f"👍 Лайки: {likes}, 🔄 Ретвиты: {retweets}\n"

        result += f"🔗 {tweet_url}\n\n"
        result += "Бот будет отправлять уведомления о новых твитах."

        # Проверяем наличие медиа для включения превью
        disable_preview = not tweet_data.get('has_media', False) and not tweet_data.get('media')

        await message.edit_text(result, disable_web_page_preview=disable_preview)
    else:
        # Упрощенная версия, если полные данные не доступны
        result = (f"✅ Добавлен @{username}\n\n"
                  f"🆔 ID последнего твита: {tweet_id}\n"
                  f"🔍 Метод проверки: {method}\n"
                  f"🔗 https://twitter.com/{username}/status/{tweet_id}\n\n"
                  f"Бот будет отправлять уведомления о новых твитах.")

        await message.edit_text(result)


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет аккаунт из отслеживания"""
    if not context.args:
        return await update.message.reply_text("Использование: /remove <username>")

    username = context.args[0].lstrip("@")
    accounts = init_accounts()

    if username.lower() not in accounts:
        return await update.message.reply_text(f"@{username} не найден в списке.")

    del accounts[username.lower()]
    save_accounts(accounts)

    # Очищаем кеш для удаленного аккаунта
    delete_from_cache("tweets", f"web_{username.lower()}")
    delete_from_cache("tweets", f"nitter_{username.lower()}")
    delete_from_cache("tweets", f"api_{username.lower()}")
    delete_from_cache("users", username.lower())

    await update.message.reply_text(f"✅ Удалён @{username}.")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список отслеживаемых аккаунтов"""
    accounts = init_accounts()

    if not accounts:
        if hasattr(update, 'callback_query') and update.callback_query:
            return await update.callback_query.edit_message_text(
                "Список пуст. Добавьте аккаунты с помощью команды /add <username>"
            )
        else:
            return await update.message.reply_text(
                "Список пуст. Добавьте аккаунты с помощью команды /add <username>"
            )

    settings = get_settings()
    interval_mins = settings["check_interval"] // 60
    enabled = settings.get("enabled", True)
    status = "✅" if enabled else "❌"
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    msg = f"⚙️ Настройки:\n• Интервал проверки: {interval_mins} мин.\n• Мониторинг: {status}\n• Методы по умолчанию: {', '.join(methods)}\n\n"
    msg += f"📋 Аккаунты ({len(accounts)}):\n"

    for username, data in sorted(accounts.items(), key=lambda x: x[1].get("priority", 1.0), reverse=True):
        display_name = data.get('username', username)
        last_check = data.get("last_check", "никогда")
        tweet_id = data.get("last_tweet_id", "нет")
        method = data.get("check_method", "unknown")
        success_rate = data.get("success_rate", 100.0)
        tweet_text = data.get("last_tweet_text", "")
        formatted_date = data.get("tweet_data", {}).get("formatted_date", "")

        # Добавляем информацию о методах скрапинга
        scraper_methods = data.get("scraper_methods")
        methods_info = f"общие ({', '.join(settings.get('scraper_methods', ['nitter', 'web', 'api']))})" if scraper_methods is None else ', '.join(
            scraper_methods)

        # Если методы полностью отключены
        if scraper_methods == []:
            methods_info = "❌ отключен"

        if last_check != "никогда":
            try:
                check_dt = datetime.fromisoformat(last_check)
                last_check = check_dt.strftime("%Y-%m-%d %H:%M")
            except:
                last_check = "недавно"

        account_line = f"• @{display_name}"
        if formatted_date:
            account_line += f" ({formatted_date})"

        account_line += f"\n  ID: {tweet_id}, {success_rate:.0f}%, метод: {method}, проверка: {last_check}"
        account_line += f"\n  🛠 Методы: {methods_info}"
        msg += account_line

        if tweet_text:
            short_text = tweet_text[:50] + "..." if len(tweet_text) > 50 else tweet_text
            msg += f"\n  ➡️ {short_text}"

        msg += "\n\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проверить аккаунты", callback_data="check")],
        [InlineKeyboardButton("🧹 Очистить кеш", callback_data="clearcache")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает последние найденные твиты без проверки"""
    if hasattr(update, 'callback_query') and update.callback_query:
        message = await update.callback_query.edit_message_text(
            "Загружаем последние найденные твиты..."
        )
    else:
        message = await update.message.reply_text(
            "Загружаем последние найденные твиты..."
        )

    accounts = init_accounts()

    if not accounts:
        return await message.edit_text(
            "Список пуст. Добавьте аккаунты с помощью команды /add <username>"
        )

    results = []

    for username, account in accounts.items():
        display_name = account.get('username', username)
        last_id = account.get('last_tweet_id')
        last_check = account.get('last_check', 'никогда')
        method = account.get('check_method', 'unknown')
        tweet_data = account.get('tweet_data', {})

        if last_check != 'никогда':
            try:
                check_dt = datetime.fromisoformat(last_check)
                last_check = check_dt.strftime("%Y-%m-%d %H:%M")
            except:
                last_check = "недавно"

        if last_id:
            # Формируем подробное представление твита из сохраненных данных
            tweet_text = tweet_data.get('text', account.get('last_tweet_text', '[Текст недоступен]'))
            tweet_url = tweet_data.get('url', account.get('last_tweet_url',
                                                          f"https://twitter.com/{display_name}/status/{last_id}"))
            formatted_date = tweet_data.get('formatted_date', '')
            browser_used = tweet_data.get('browser_used', '')

            tweet_info = f"📱 @{display_name}"

            # Добавляем дату, если она есть
            if formatted_date:
                tweet_info += f" ({formatted_date})"

            tweet_info += f"\n➡️ {tweet_text}"

            # Добавляем метрики, если они есть
            likes = tweet_data.get('likes', 0)
            retweets = tweet_data.get('retweets', 0)

            if likes or retweets:
                tweet_info += f"\n👍 {likes} · 🔄 {retweets}"

            # Добавляем метод и время проверки
            method_info = method
            if browser_used:
                method_info += f" · {browser_used}"

            tweet_info += f"\n🔍 Метод: {method_info}, проверка: {last_check}"

            # Добавляем URL в конце
            tweet_info += f"\n🔗 {tweet_url}"

            results.append(tweet_info)
        else:
            results.append(f"❓ @{display_name}: твиты не найдены")

    result_text = "📊 Последние найденные твиты:\n\n" + "\n\n".join(results)

    if len(result_text) > 4000:
        result_text = result_text[:3997] + "..."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Проверить принудительно", callback_data="check_force")],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")]
    ])

    await message.edit_text(result_text, reply_markup=keyboard, disable_web_page_preview=True)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает настройки бота"""
    settings = get_settings()

    interval_mins = settings.get("check_interval", DEFAULT_CHECK_INTERVAL) // 60
    enabled = settings.get("enabled", True)
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])
    parallel_checks = settings.get("parallel_checks", 3)
    api_request_limit = settings.get("api_request_limit", 20)
    randomize = settings.get("randomize_intervals", True)

    enabled_status = "✅ включен" if enabled else "❌ выключен"
    proxies_status = "✅ включено" if use_proxies else "❌ выключено"
    randomize_status = "✅ включено" if randomize else "❌ выключено"

    proxies = get_proxies()
    proxy_count = len(proxies.get("proxies", []))

    nitter_instances = settings.get("nitter_instances", NITTER_INSTANCES)
    nitter_count = len(nitter_instances)

    msg = (
        "⚙️ **Настройки мониторинга**\n\n"
        f"• Мониторинг: {enabled_status}\n"
        f"• Интервал проверки: {interval_mins} мин.\n"
        f"• Случайные интервалы: {randomize_status}\n"
        f"• Одновременные проверки: {parallel_checks}\n"
        f"• Лимит API запросов: {api_request_limit}\n"
        f"• Использование прокси: {proxies_status} (доступно: {proxy_count})\n"
        f"• Nitter-инстансы: {nitter_count}\n\n"
        f"• Приоритет методов: {', '.join(methods)}\n\n"
    )

    keyboard = []

    keyboard.append([
        InlineKeyboardButton("🔄 Вкл/выкл мониторинг", callback_data="toggle_monitoring"),
        InlineKeyboardButton("🔌 Вкл/выкл прокси", callback_data="toggle_proxies")
    ])

    keyboard.append([
        InlineKeyboardButton("Nitter", callback_data="method_priority:nitter"),
        InlineKeyboardButton("Web", callback_data="method_priority:web"),
        InlineKeyboardButton("API", callback_data="method_priority:api")
    ])

    keyboard.append([
        InlineKeyboardButton("⏱ Интервал", callback_data="set_interval"),
        InlineKeyboardButton("🧹 Очистить кеш", callback_data="clearcache"),
        InlineKeyboardButton("🔄 Обновить Nitter", callback_data="update_nitter")
    ])

    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="list")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")


async def cmd_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает методы скрапинга для аккаунта"""
    message = update.effective_message
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await message.reply_text("⛔️ У вас нет доступа к этой команде.")
        return

    # Получаем аргументы команды
    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            "📝 Использование: `/methods username методы"
            "`\n\n"
            "Доступные методы: `api`, `web`, `nitter`\n"
            "Пример: `/methods n2sheiner nitter,web,api`\n"
            "Для сброса к общим настройкам: `/methods elonmusk reset`\n"
            "Для полного отключения аккаунта: `/methods elonmusk clear`",
            parse_mode="Markdown"
        )
        return

    username = args[0].replace("@", "")
    methods_str = args[1].lower()

    # Загружаем аккаунты
    accounts = init_accounts()

    if username.lower() not in accounts:
        await message.reply_text(f"❌ Аккаунт @{username} не найден.")
        return

    # Если это сброс настроек к общим
    if methods_str == "reset":
        accounts[username.lower()]["scraper_methods"] = None
        save_accounts(accounts)

        # Получаем общие методы для отображения
        settings = get_settings()
        common_methods = settings.get("scraper_methods", ["nitter", "web", "api"])

        await message.reply_text(
            f"✅ Настройки скрапинга для @{username} сброшены до общих.\n"
            f"Будут использоваться методы: {', '.join(common_methods)}"
        )
        return

    # Если это полная очистка методов (отключение аккаунта)
    if methods_str == "clear":
        accounts[username.lower()]["scraper_methods"] = []
        save_accounts(accounts)
        await message.reply_text(f"✅ Методы скрапинга для @{username} полностью очищены. Аккаунт отключен.")
        return

    # Разбираем список методов
    methods = [m.strip() for m in methods_str.split(',')]
    valid_methods = []

    for m in methods:
        if m in ["api", "web", "nitter"]:
            valid_methods.append(m)

    if not valid_methods:
        await message.reply_text("❌ Не указаны допустимые методы (`api`, `web`, `nitter`)")
        return

    # Сохраняем настройки
    accounts[username.lower()]["scraper_methods"] = valid_methods
    save_accounts(accounts)

    await message.reply_text(
        f"✅ Для @{username} установлены методы: {', '.join(valid_methods)}\n"
        f"Порядок определяет приоритет использования."
    )


async def cmd_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает Safari WebDriver с поддержкой ручного ввода капчи"""
    global safari_driver

    message = update.effective_message
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await message.reply_text("⛔️ У вас нет доступа к этой команде.")
        return

    status_msg = await message.reply_text(
        "🔄 Инициализация Safari WebDriver...\n\n"
        "⚠️ ВАЖНО: Когда откроется окно Safari:\n\n"
        "1. Появится предупреждение 'This Safari window is remotely controlled'.\n"
        "2. Нажмите 'Continue Session'\n"
        "3. Если появится капча, вы сможете ввести её вручную\n"
        "4. После этого бот продолжит работу автоматически\n\n"
    )

    try:
        # Включаем Safari WebDriver
        try:
            subprocess.run(['sudo', 'safaridriver', '--enable'], check=False)
            logger.info("SafariDriver включен")
        except:
            pass

        # Инициализируем WebDriver, если его еще нет
        if safari_driver is None:
            options = SafariOptions()
            safari_driver = webdriver.Safari(options=options)
            safari_driver.set_page_load_timeout(25)
            safari_driver.implicitly_wait(10)
            logger.info("Safari WebDriver создан")

        # Открываем Twitter в WebDriver
        safari_driver.get("https://twitter.com/home")
        logger.info("Twitter открыт в Safari WebDriver")

        await status_msg.edit_text(
            status_msg.text + "\n✅ Safari WebDriver запущен!\n\n"
                              "1. В окне Safari нажмите 'Continue Session'\n"
                              "2. Войдите в Twitter, если требуется\n"
                              "3. Решите капчу, если она появится\n"
                              "4. После авторизации нажмите кнопку ниже"
        )

        # Добавляем кнопку для подтверждения завершения
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Готово, я авторизовался", callback_data="auth_completed")
        ]])

        await message.reply_text("Нажмите кнопку после авторизации:", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при запуске Safari WebDriver: {e}")
        await status_msg.edit_text(f"Ошибка при запуске Safari WebDriver: {str(e)}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику веб-скрапинга"""
    if not os.path.exists(BROWSER_STATS_FILE):
        return await update.message.reply_text("Статистика браузеров еще не собрана.")

    try:
        with open(BROWSER_STATS_FILE, 'r') as f:
            stats = json.load(f)

        msg = "📊 **Статистика браузеров**\n\n"

        for browser, data in stats["browsers"].items():
            total = data.get("total_attempts", 0)
            successful = data.get("successful_attempts", 0)
            success_rate = (successful / total * 100) if total > 0 else 0
            captchas = data.get("captchas", 0)
            errors = data.get("errors", 0)

            # Форматируем время последнего успеха
            last_success = data.get("last_success")
            if last_success:
                last_success_str = datetime.fromtimestamp(last_success).strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_success_str = "нет данных"

            msg += f"**{browser}**\n"
            msg += f"- Всего попыток: {total}\n"
            msg += f"- Успешных: {successful} ({success_rate:.1f}%)\n"
            msg += f"- Капчи: {captchas}\n"
            msg += f"- Ошибки: {errors}\n"
            msg += f"- Последний успех: {last_success_str}\n\n"

        last_update = stats.get("last_update", 0)
        last_update_str = datetime.fromtimestamp(last_update).strftime("%Y-%m-%d %H:%M:%S")
        msg += f"Последнее обновление: {last_update_str}"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка при получении статистики браузеров: {e}")
        await update.message.reply_text(f"Ошибка при получении статистики: {str(e)}")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Полностью сбрасывает данные аккаунта"""
    if not context.args:
        return await update.message.reply_text("Использование: /reset <username>")

    username = context.args[0].lstrip("@")
    accounts = init_accounts()

    if username.lower() not in accounts:
        return await update.message.reply_text(f"@{username} не найден в списке.")

    message = await update.message.reply_text(f"Сброс данных для аккаунта @{username}...")

    # Полная очистка данных по аккаунту
    clean_account_data(username)

    # Повторная инициализация
    await message.edit_text(
        f"✅ Данные для аккаунта @{username} полностью сброшены.\n"
        "Будет выполнена повторная проверка при следующем обновлении."
    )


async def cmd_update_nitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет список Nitter-инстансов"""
    message = await update.message.reply_text("🔍 Проверка доступных Nitter-инстансов...")

    try:
        instances = await update_nitter_instances()

        if instances:
            await message.edit_text(
                f"✅ Найдено {len(instances)} рабочих Nitter-инстансов:\n\n" +
                "\n".join(f"• {instance}" for instance in instances[:10]) +
                ("\n\n...и ещё больше" if len(instances) > 10 else "")
            )
        else:
            await message.edit_text(
                "❌ Не найдено работающих Nitter-инстансов. Будет использоваться прямой скрапинг Twitter."
            )
    except Exception as e:
        await message.edit_text(f"❌ Ошибка при обновлении: {str(e)}")


async def cmd_clearcache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает кеш для обновления данных"""
    # Если вызвано из меню
    if hasattr(update, 'callback_query') and update.callback_query:
        message = await update.callback_query.edit_message_text("Очистка кеша...")
    else:
        message = await update.message.reply_text("Очистка кеша...")

    accounts = init_accounts()

    if not accounts:
        await message.edit_text("Нет отслеживаемых аккаунтов.")
        return

    # Очищаем кеш для всех аккаунтов
    for username in accounts:
        delete_from_cache("tweets", f"web_{username.lower()}")
        delete_from_cache("tweets", f"nitter_{username.lower()}")
        delete_from_cache("tweets", f"api_{username.lower()}")

    await message.edit_text(
        f"✅ Кеш очищен для {len(accounts)} аккаунтов.\n\n"
        "При следующей проверке будут получены свежие данные."
    )


async def set_interval_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню для установки интервала проверки"""
    settings = get_settings()
    current_mins = settings["check_interval"] // 60

    msg = f"⏱ Текущий интервал проверки: {current_mins} минут\n\nВыберите новый интервал:"

    keyboard = []
    # Добавляем кнопки для различных интервалов
    intervals = [5, 10, 15, 30, 60, 120]
    row = []

    for interval in intervals:
        btn_text = f"{interval} мин" + (" ✓" if current_mins == interval else "")
        row.append(InlineKeyboardButton(btn_text, callback_data=f"interval:{interval}"))
        if len(row) == 3:  # По 3 кнопки в ряд
            keyboard.append(row)
            row = []

    if row:  # Добавляем оставшиеся кнопки
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)


async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE, interval_str):
    """Устанавливает интервал проверки"""
    try:
        interval = int(interval_str)
        if interval < 1:
            interval = 1
        if interval > 1440:
            interval = 1440

        update_setting("check_interval", interval * 60)
        await cmd_settings(update, context)

    except ValueError:
        await update.callback_query.edit_message_text(
            "⚠️ Ошибка при установке интервала. Пожалуйста, выберите другое значение.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="set_interval")
            ]])
        )


async def update_nitter_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет список Nitter-инстансов"""
    message = await update.callback_query.edit_message_text("🔍 Проверка доступных Nitter-инстансов...")

    try:
        instances = await update_nitter_instances()

        if instances:
            # Ограничиваем вывод до 5 инстансов для краткости
            instances_display = instances[:5]
            more_count = len(instances) - len(instances_display)

            text = f"✅ Найдено {len(instances)} рабочих Nitter-инстансов:\n\n" + \
                   "\n".join(f"• {instance}" for instance in instances_display)

            if more_count > 0:
                text += f"\n\n...и ещё {more_count} инстансов."

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="settings")
            ]])

            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.edit_text(
                "❌ Не найдено работающих Nitter-инстансов. Будет использоваться прямой скрапинг Twitter.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Назад", callback_data="settings")
                ]])
            )
    except Exception as e:
        await message.edit_text(
            f"❌ Ошибка при обновлении: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="settings")
            ]])
        )


async def toggle_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включает/выключает использование прокси"""
    settings = get_settings()
    current = settings.get("use_proxies", False)
    settings["use_proxies"] = not current
    save_json(SETTINGS_FILE, settings)

    # Переходим обратно в настройки
    await cmd_settings(update, context)


async def toggle_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включает/выключает мониторинг"""
    settings = get_settings()
    current = settings.get("enabled", True)
    settings["enabled"] = not current
    save_json(SETTINGS_FILE, settings)

    # Переходим обратно в настройки
    await cmd_settings(update, context)


async def change_method_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, method):
    """Изменяет приоритет методов проверки"""
    settings = get_settings()
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    # Перемещаем выбранный метод в начало списка
    if method in methods:
        methods.remove(method)
    methods.insert(0, method)

    # Сохраняем обновленное значение
    settings["scraper_methods"] = methods
    save_json(SETTINGS_FILE, settings)

    # Возвращаемся в настройки
    await cmd_settings(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        await cmd_list(update, context)
    elif query.data == "check":
        await cmd_check(update, context)
    elif query.data == "check_force":
        await cmd_clearcache(update, context)
        await asyncio.sleep(1)
        await check_all_accounts(update, context)
    elif query.data == "settings":
        await cmd_settings(update, context)
    elif query.data == "toggle_proxies":
        await toggle_proxies(update, context)
    elif query.data == "toggle_monitoring":
        await toggle_monitoring(update, context)
    elif query.data == "clearcache":
        await cmd_clearcache(update, context)
    elif query.data == "set_interval":
        await set_interval_menu(update, context)
    elif query.data == "update_nitter":
        await update_nitter_menu(update, context)
    elif query.data.startswith("interval:"):
        await set_interval(update, context, query.data.split(":", 1)[1])
    elif query.data.startswith("method_priority:"):
        method = query.data.split(":", 1)[1]
        await change_method_priority(update, context, method)
    # ... существующие обработчики кнопок
    elif query.data == "auth_completed":
        await query.edit_message_text(
            "✅ Авторизация сохранена!\n\n"
            "Теперь бот будет использовать авторизованную сессию для скрапинга.\n"
            "Когда появится капча, вы сможете решить её вручную."
        )
    elif query.data == "twitter_auth_done":
        global safari_driver

        await query.edit_message_text("Инициализация Safari WebDriver...")

        try:
            # Проверим доступна ли уже инициализация
            if safari_driver is None:
                options = SafariOptions()
                safari_driver = webdriver.Safari(options=options)
                safari_driver.set_page_load_timeout(25)
                safari_driver.implicitly_wait(10)

            # Проверяем что мы залогинены в Twitter
            safari_driver.get("https://twitter.com/home")
            time.sleep(3)

            # Проверяем URL - если мы на странице логина, значит не вошли
            current_url = safari_driver.current_url
            if "login" in current_url:
                await query.edit_message_text(
                    "❌ Кажется, вы не вошли в Twitter. Пожалуйста, войдите и попробуйте снова."
                )
            else:
                await query.edit_message_text(
                    "✅ Safari WebDriver успешно инициализирован! Вы можете использовать метод web для скрапинга."
                )
        except Exception as e:
            logger.error(f"Ошибка инициализации WebDriver: {e}")
            await query.edit_message_text(f"Ошибка: {str(e)}")

async def check_all_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно проверяет все аккаунты"""
    if hasattr(update, 'callback_query') and update.callback_query:
        message = await update.callback_query.edit_message_text("Проверяем твиты...")
    else:
        message = await update.message.reply_text("Проверяем твиты...")

    accounts = init_accounts()

    if not accounts:
        return await message.edit_text("Список пуст. Добавьте аккаунты с помощью команды /add <username>")

    settings = get_settings()
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    results = []
    new_tweets = []
    accounts_updated = False

    # Для каждого аккаунта выполняем проверку
    for username, account in accounts.items():
        display_name = account.get('username', username)
        last_id = account.get('last_tweet_id')
        first_check = account.get('first_check', False)
        account_methods = account.get('scraper_methods', methods)

        # Пропускаем аккаунты с пустым списком методов
        if account_methods == []:
            results.append(f"⏭️ @{display_name}: пропущен (методы отключены)")
            continue

        account['last_check'] = datetime.now().isoformat()
        account['check_count'] = account.get('check_count', 0) + 1
        accounts_updated = True

        try:
            # Очищаем кеш для гарантии получения свежих данных
            delete_from_cache("tweets", f"web_{username.lower()}")
            delete_from_cache("tweets", f"nitter_{username.lower()}")
            delete_from_cache("tweets", f"api_{username.lower()}")

            user_id, tweet_id, tweet_data, method = await check_tweet_multi_method(
                display_name, account_methods, use_proxies
            )

            if user_id and not account.get('user_id'):
                account['user_id'] = user_id
                accounts_updated = True

            if not tweet_id:
                account['fail_count'] = account.get('fail_count', 0) + 1
                total_checks = account.get('check_count', 1)
                fail_count = account.get('fail_count', 0)
                account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

                if last_id:
                    results.append(f"❓ @{display_name}: твиты не найдены, последний известный ID: {last_id}")
                else:
                    results.append(f"❓ @{display_name}: твиты не найдены")
                continue

            if account.get('fail_count', 0) > 0:
                account['fail_count'] = max(0, account.get('fail_count', 0) - 1)

            total_checks = account.get('check_count', 1)
            fail_count = account.get('fail_count', 0)
            account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

            account['check_method'] = method

            if tweet_data:
                tweet_text = tweet_data.get('text', '[Текст недоступен]')
                tweet_url = tweet_data.get('url', f"https://twitter.com/{display_name}/status/{tweet_id}")
                account['last_tweet_text'] = tweet_text
                account['last_tweet_url'] = tweet_url
                account['tweet_data'] = tweet_data

            if first_check:
                account['first_check'] = False
                account['last_tweet_id'] = tweet_id
                accounts_updated = True

                tweet_text = tweet_data.get('text', '[Текст недоступен]') if tweet_data else '[Текст недоступен]'
                tweet_url = tweet_data.get('url',
                                           f"https://twitter.com/{display_name}/status/{tweet_id}") if tweet_data else f"https://twitter.com/{display_name}/status/{tweet_id}"
                results.append(
                    f"📝 @{display_name}: первая проверка, сохранен ID твита {tweet_id}\n➡️ Текст: {tweet_text[:50]}...")
            elif tweet_id != last_id:
                try:
                    is_newer = int(tweet_id) > int(last_id)
                except (ValueError, TypeError):
                    is_newer = True

                if is_newer:
                    account['last_tweet_id'] = tweet_id
                    accounts_updated = True

                    # Формируем подробное сообщение с данными о твите
                    tweet_text = tweet_data.get('text', '[Текст недоступен]')
                    tweet_url = tweet_data.get('url', f"https://twitter.com/{display_name}/status/{tweet_id}")
                    formatted_date = tweet_data.get('formatted_date', '')

                    tweet_msg = f"🔥 Новый твит от @{display_name}"
                    if formatted_date:
                        tweet_msg += f" ({formatted_date})"

                    tweet_msg += f":\n\n{tweet_text[:50]}..."

                    # Добавляем метрики, если они есть
                    likes = tweet_data.get('likes', 0)
                    retweets = tweet_data.get('retweets', 0)
                    if likes or retweets:
                        tweet_msg += f"\n\n👍 {likes} · 🔄 {retweets}"

                    new_tweets.append((display_name, tweet_id, tweet_data))
                    results.append(f"✅ @{display_name}: новый твит {tweet_id} (метод: {method})")
                else:
                    account['last_tweet_id'] = tweet_id
                    accounts_updated = True
                    results.append(f"🔄 @{display_name}: обновлен ID твита на {tweet_id} (метод: {method})")
            else:
                results.append(f"🔄 @{display_name}: нет новых твитов (метод: {method})")

        except Exception as e:
            logger.error(f"Ошибка при проверке @{display_name}: {e}")
            results.append(f"❌ @{display_name}: ошибка - {str(e)[:50]}")
            account['fail_count'] = account.get('fail_count', 0) + 1

    if accounts_updated:
        save_accounts(accounts)

    if new_tweets:
        await message.edit_text(f"✅ Найдено {len(new_tweets)} новых твитов!")

        # Отправляем уведомления о новых твитах
        subs = [update.effective_chat.id]  # Отправляем только текущему пользователю
        for username, tweet_id, tweet_data in new_tweets:
            await send_tweet_with_media(context.application, subs, username, tweet_id, tweet_data)
    else:
        result_text = "🔍 Новых твитов не найдено.\n\n📊 Результаты проверки:\n" + "\n".join(results)

        if len(result_text) > 4000:
            result_text = result_text[:3997] + "..."

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Проверить снова", callback_data="check_force"),
            InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")
        ]])

        await message.edit_text(result_text, reply_markup=keyboard)


async def check_instance(session, instance):
    """Проверяет доступность Nitter-инстанса"""
    try:
        async with session.get(
                f"{instance}/twitter",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
        ) as response:
            if response.status != 200:
                return False

            # Проверка содержимого страницы, чтобы убедиться, что это работающий инстанс
            page_content = await response.text()
            return 'twitter' in page_content.lower() and len(page_content) > 1000
    except:
        return False


async def check_nitter_instance_status(instance):
    """Проверяет работоспособность Nitter-инстанса"""
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # Короткий таймаут
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{instance}/", headers={"User-Agent": "Mozilla/5.0"}) as response:
                if response.status == 200:
                    try:
                        text = await response.text()
                        if "nitter" in text.lower() or "twitter" in text.lower():
                            return True
                    except:
                        pass
        return False
    except:
        return False


async def get_working_nitter_instances():
    """Возвращает список работающих Nitter-инстансов"""
    working_instances = []
    tasks = [check_nitter_instance_status(instance) for instance in NITTER_INSTANCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, is_working in enumerate(results):
        if is_working and not isinstance(is_working, Exception):
            working_instances.append(NITTER_INSTANCES[i])
            logger.info(f"Nitter инстанс доступен: {NITTER_INSTANCES[i]}")

    if working_instances:
        return working_instances
    else:
        logger.warning("Нет доступных Nitter-инстансов. Используем список по умолчанию.")
        # Возвращаем первые 3 инстанса из списка, даже если они не работают
        return NITTER_INSTANCES[:3]


async def update_nitter_instances():
    """Проверяет и обновляет список рабочих Nitter-инстансов"""
    # Проверяем, что цикл событий запущен
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        logger.error("Невозможно обновить Nitter-инстансы: цикл событий не запущен")
        return []

    working_instances = []

    try:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for instance in NITTER_INSTANCES:
                tasks.append(check_instance(session, instance))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for instance, is_working in zip(NITTER_INSTANCES, results):
                if is_working and not isinstance(is_working, Exception):
                    working_instances.append(instance)
                    logger.info(f"Nitter instance available: {instance}")

        if not working_instances:
            logger.warning("No Nitter instances available, using the default list")
            working_instances = NITTER_INSTANCES[:3]  # Берем хотя бы первые 3 инстанса по умолчанию

        settings = get_settings()
        settings["nitter_instances"] = working_instances
        settings["last_health_check"] = int(time.time())
        save_json(SETTINGS_FILE, settings)

        return working_instances
    except Exception as e:
        logger.error(f"Ошибка при обновлении Nitter-инстансов: {e}")
        return NITTER_INSTANCES[:3]  # В случае ошибки возвращаем первые 3 инстанса


def main():
    if not TG_TOKEN:
        logger.error("TG_TOKEN не указан в .env файле")
        return

    for path, default in [
        (SUBSCRIBERS_FILE, []),
        (SETTINGS_FILE, {
            "check_interval": DEFAULT_CHECK_INTERVAL,
            "enabled": True,
            "use_proxies": False,
            "scraper_methods": ["nitter", "web", "api"],
            "max_retries": 3,
            "cache_expiry": 1800,
            "randomize_intervals": True,
            "min_interval_factor": 0.8,
            "max_interval_factor": 1.2,
            "parallel_checks": 3,
            "api_request_limit": 20,
            "nitter_instances": NITTER_INSTANCES,
            "health_check_interval": 1800,  # 30 минут
            "last_health_check": 0
        })
    ]:
        if not os.path.exists(path):
            save_json(path, default)

    # Проверяем наличие файла статистики браузеров
    if not os.path.exists(BROWSER_STATS_FILE):
        save_json(BROWSER_STATS_FILE, {"browsers": {}, "last_update": int(time.time())})

    app = ApplicationBuilder().token(TG_TOKEN).post_init(on_startup).post_shutdown(on_shutdown).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("clearcache", cmd_clearcache))
    app.add_handler(CommandHandler("interval", set_interval_menu))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("methods", cmd_methods))
    app.add_handler(CommandHandler("auth", cmd_auth))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("update_nitter", cmd_update_nitter))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("auth_google", cmd_auth_google))
    app.add_handler(CommandHandler("set_google_credentials", cmd_set_google_credentials))
    app.add_handler(CommandHandler("auth_google_simple", cmd_auth_google_simple))
    app.add_handler(CallbackQueryHandler(button_handler))

    settings = get_settings()
    interval_mins = settings["check_interval"] // 60
    logger.info(f"🚀 Бот запущен, интервал проверки: {interval_mins} мин.")
    try:
        app.run_polling(close_loop=False)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()