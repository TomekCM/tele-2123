import os
import json
import logging
import asyncio
import time
import random
import requests
import re
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import quote
import aiohttp
import traceback

# Конфигурация логирования
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройки
DEFAULT_CHECK_INTERVAL = 600  # секунд (10 минут)
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
TWITTER_BEARER = os.getenv("TWITTER_BEARER", "")

# Пути к файлам
DATA_DIR = "data"
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
API_LIMITS_FILE = os.path.join(DATA_DIR, "api_limits.json")
PROXIES_FILE = os.path.join(DATA_DIR, "proxies.json")

# Создаем директорию, если её нет
os.makedirs(DATA_DIR, exist_ok=True)


# Утилиты для работы с JSON
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Управление настройками
def get_settings():
    return load_json(SETTINGS_FILE, {
        "check_interval": DEFAULT_CHECK_INTERVAL,
        "enabled": True,
        "use_proxies": False,
        "scraper_methods": ["nitter", "web", "api"],  # Приоритет методов
        "max_retries": 3,
        "cache_expiry": 3600,  # Срок действия кеша в секундах
        "randomize_intervals": True,
        "min_interval_factor": 0.8,  # Минимальный множитель для случайного интервала
        "max_interval_factor": 1.2,  # Максимальный множитель
        "parallel_checks": 3,  # Число параллельных проверок
        "nitter_instances": []  # Будет заполнено при запуске
    })


def update_setting(key, value):
    settings = get_settings()
    settings[key] = value
    save_json(SETTINGS_FILE, settings)
    return settings


# Управление прокси
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


# Инициализация или миграция данных аккаунтов
def init_accounts():
    """Инициализирует или мигрирует данные аккаунтов"""
    try:
        # Создаем файл, если его нет
        if not os.path.exists(ACCOUNTS_FILE):
            save_json(ACCOUNTS_FILE, {})
            return {}

        # Загружаем данные
        accounts = load_json(ACCOUNTS_FILE, {})

        # Если это список (старый формат), конвертируем в словарь
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
                        "check_count": 0,  # Счетчик проверок для статистики
                        "success_rate": 100.0,  # Процент успешных проверок
                        "fail_count": 0,  # Счетчик неудачных проверок
                        "check_method": None,  # Последний успешный метод проверки
                        "priority": 1.0  # Приоритет проверки (1.0 - стандартный)
                    }
            save_json(ACCOUNTS_FILE, new_accounts)
            return new_accounts

        # Обновляем формат аккаунтов, если нужно
        updated = False
        for username, account in accounts.items():
            # Добавляем новые поля, если их нет
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

        if updated:
            save_json(ACCOUNTS_FILE, accounts)

        return accounts
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных аккаунтов: {e}")
        # В случае ошибки возвращаем и сохраняем пустой словарь
        save_json(ACCOUNTS_FILE, {})
        return {}


async def update_nitter_instances():
    """Обновляет список рабочих Nitter-инстансов"""
    # Базовый список известных Nitter-инстансов
    known_instances = [
        "https://nitter.net",
        "https://nitter.unixfox.eu",
        "https://nitter.domains",
        "https://nitter.privacydev.net",
        "https://nitter.fdn.fr",
        "https://nitter.priv.pw",
        "https://bird.trom.tf",
        "https://nitter.poast.org",
        "https://nitter.d420.de",
        "https://nitter.caioalonso.com",
        "https://nitter.at",
        "https://nttr.stream",
        "https://nitter.pw",
        "https://nitter.bird.froth.zone"
    ]

    # Список рабочих инстансов
    working_instances = []

    # Проверяем каждый инстанс
    async with aiohttp.ClientSession() as session:
        for instance in known_instances:
            try:
                # Используем небольшой таймаут для быстрой проверки
                async with session.get(f"{instance}/twitter", timeout=5) as response:
                    if response.status == 200:
                        working_instances.append(instance)
                        logger.info(f"Nitter-инстанс доступен: {instance}")
            except Exception as e:
                logger.debug(f"Nitter-инстанс недоступен: {instance} - {str(e)}")

    # Если нашли хотя бы один рабочий инстанс
    if working_instances:
        # Обновляем список в настройках
        settings = get_settings()
        settings["nitter_instances"] = working_instances
        save_json(SETTINGS_FILE, settings)
        logger.info(f"Обновлен список Nitter-инстансов: найдено {len(working_instances)} рабочих")
        return working_instances
    else:
        logger.warning("Не найдено ни одного работающего Nitter-инстанса")
        return []


# Методы для работы с Twitter
class TwitterClient:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.rate_limited = False
        self.rate_limit_reset = 0
        self.user_agent = UserAgent().random
        self.cache = {}  # Простой кэш для уменьшения запросов
        self.session = requests.Session()

    def clear_cache(self):
        """Очищает кэш запросов"""
        self.cache = {}

    def update_user_agent(self):
        """Обновляет User-Agent для разных запросов"""
        self.user_agent = UserAgent().random

    def check_rate_limit(self):
        """Проверяет, не превышены ли лимиты API"""
        if self.rate_limited:
            now = time.time()
            if now < self.rate_limit_reset:
                return False
            else:
                self.rate_limited = False
        return True

    def set_rate_limit(self, reset_time):
        """Устанавливает время сброса лимитов"""
        self.rate_limited = True
        self.rate_limit_reset = reset_time

    def get_cache_key(self, method, identifier):
        """Создает ключ для кэширования"""
        return f"{method}:{identifier}"

    def get_cached_data(self, cache_key, max_age=3600):
        """Получает данные из кэша если они свежие"""
        if cache_key in self.cache:
            item = self.cache[cache_key]
            if time.time() - item['timestamp'] < max_age:
                return item['data']
        return None

    def set_cache(self, cache_key, data):
        """Сохраняет данные в кэш"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    def get_user_by_username(self, username):
        """Получает информацию о пользователе по имени"""
        if not self.bearer_token or not self.check_rate_limit():
            return None

        # Проверяем кэш
        cache_key = self.get_cache_key("user", username.lower())
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached

        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.user_agent
        }

        try:
            response = self.session.get(url, headers=headers, timeout=10)

            # Обработка лимитов
            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 900))
                self.set_rate_limit(reset_time)
                logger.warning(f"Достигнут лимит API для получения пользователя, сброс в {reset_time}")
                return None

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    # Сохраняем в кэш
                    self.set_cache(cache_key, data["data"])
                    return data["data"]
            else:
                logger.error(f"Ошибка при получении пользователя: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Ошибка запроса к API: {e}")

        return None

    def get_user_tweets(self, user_id, use_proxies=False):
        """Получает последние твиты пользователя"""
        if not self.bearer_token or not self.check_rate_limit():
            return None

        # Проверяем кэш (с меньшим сроком действия для твитов)
        cache_key = self.get_cache_key("tweets", user_id)
        cached = self.get_cached_data(cache_key, 300)  # 5 минут для твитов
        if cached:
            return cached

        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": 5,  # Минимально допустимое значение
            "tweet.fields": "created_at,text",
            "exclude": "retweets,replies"
        }
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.user_agent
        }

        try:
            # Используем прокси, если включено
            proxies = get_random_proxy() if use_proxies else None

            response = self.session.get(url, headers=headers, params=params, proxies=proxies, timeout=10)

            # Обработка лимитов
            if response.status_code == 429:
                reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 900))
                self.set_rate_limit(reset_time)
                logger.warning(f"Достигнут лимит API для получения твитов, сброс в {reset_time}")
                return None

            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                # Сохраняем в кэш
                self.set_cache(cache_key, tweets)
                return tweets
            else:
                logger.error(f"Ошибка при получении твитов: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Ошибка запроса к API: {e}")

        return None

    def get_latest_tweet(self, username, use_proxies=False):
        """Получает последний твит пользователя по имени через API"""
        user = self.get_user_by_username(username)
        if not user:
            return None, None, None

        user_id = user["id"]
        tweets = self.get_user_tweets(user_id, use_proxies)

        if not tweets or len(tweets) == 0:
            return user_id, None, None

        latest = tweets[0]
        tweet_id = latest["id"]
        tweet_text = latest["text"]
        tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

        return user_id, tweet_id, {"text": tweet_text, "url": tweet_url}


# Скраперы для получения твитов разными способами
class TwitterScrapers:
    def __init__(self):
        """Инициализирует класс с различными методами скрапинга"""
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        ]
        self.cache = {}
        self.session = requests.Session()
        self.async_session = None  # Будет инициализирован при необходимости

    def get_random_user_agent(self):
        """Возвращает случайный User-Agent из списка"""
        return random.choice(self.user_agents)

    def get_cache_key(self, method, username):
        """Создает ключ для кэширования"""
        return f"{method}:{username.lower()}"

    def get_cached_data(self, cache_key, max_age=300):
        """Получает данные из кэша если они свежие (по умолчанию 5 минут)"""
        if cache_key in self.cache:
            item = self.cache[cache_key]
            if time.time() - item['timestamp'] < max_age:
                return item['data']
        return None

    def set_cache(self, cache_key, data):
        """Сохраняет данные в кэш"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    async def init_async_session(self):
        """Инициализирует aiohttp сессию если она еще не создана"""
        if self.async_session is None:
            self.async_session = aiohttp.ClientSession()

    async def close_async_session(self):
        """Закрывает aiohttp сессию если она была создана"""
        if self.async_session:
            await self.async_session.close()
            self.async_session = None

    # Оригинальный метод веб-скрапинга
    def get_latest_tweet_web(self, username, use_proxies=False):
        """Получает последний твит пользователя через веб-страницу Twitter"""
        cache_key = self.get_cache_key("web", username)
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached

        url = f"https://twitter.com/{username}"

        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Referer": "https://twitter.com/",
            "sec-ch-ua": '"Chromium";v="96", "Google Chrome";v="96"',
            "sec-ch-ua-platform": '"Windows"',
        }

        try:
            # Используем прокси, если включено
            proxies = get_random_proxy() if use_proxies else None

            # Проверяем существование аккаунта
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=10)

            if response.status_code == 429:
                logger.warning(f"Ограничение запросов при скрапинге {username}, пробуем с другим юзер-агентом")
                # Пробуем еще раз с другим юзер-агентом
                headers["User-Agent"] = self.get_random_user_agent()
                time.sleep(2)  # Небольшая пауза
                response = self.session.get(url, headers=headers, proxies=proxies, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Не удалось получить страницу Twitter для {username}, код {response.status_code}")
                return None, None

            # Ищем ссылки на твиты с помощью BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Пробуем найти твиты по разным паттернам (Twitter часто меняет структуру)
            tweet_links = soup.select('a[href*="/status/"]')
            if not tweet_links:
                # Используем регулярное выражение как запасной вариант
                tweet_ids = re.findall(r'/status/(\d+)', response.text)
                if not tweet_ids:
                    logger.info(f"Твиты не найдены на странице {username}")
                    return None, None

                # Берем первый найденный ID твита
                tweet_id = tweet_ids[0]
            else:
                # Извлекаем ID из первой найденной ссылки
                href = tweet_links[0]['href']
                match = re.search(r'/status/(\d+)', href)
                if not match:
                    return None, None
                tweet_id = match.group(1)

            # Создаем URL твита
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

            # Пробуем найти текст твита
            tweet_text = "[Новый твит]"
            tweet_containers = soup.select('article[data-testid="tweet"]')
            if tweet_containers:
                text_elements = tweet_containers[0].select('div[data-testid="tweetText"]')
                if text_elements:
                    tweet_text = text_elements[0].get_text(strip=True)
                    if len(tweet_text) > 280:  # Ограничиваем длину
                        tweet_text = tweet_text[:277] + "..."

            result = (tweet_id, {"text": tweet_text, "url": tweet_url})
            self.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Ошибка при получении твита через веб для {username}: {e}")
            return None, None

    # Метод получения твитов через Nitter
    def get_latest_tweet_nitter(self, username, use_proxies=False):
        """Получает последний твит пользователя через Nitter (альтернативный фронтенд)"""
        cache_key = self.get_cache_key("nitter", username)
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached

        # Получаем список серверов Nitter для ротации из настроек или используем дефолтный
        settings = get_settings()
        nitter_instances = settings.get("nitter_instances", [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.priv.pw",
            "https://bird.trom.tf",
            "https://nitter.poast.org",
        ])

        # Если список пуст - используем хотя бы один инстанс
        if not nitter_instances:
            nitter_instances = ["https://nitter.privacydev.net"]

        # Перемешиваем список для лучшей балансировки
        random.shuffle(nitter_instances)

        # Пробуем инстансы один за другим
        for base_url in nitter_instances[:3]:  # Ограничиваем до 3 попыток
            url = f"{base_url}/{username}"

            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml",
            }

            try:
                # Используем прокси, если включено
                proxies = get_random_proxy() if use_proxies else None

                response = self.session.get(url, headers=headers, proxies=proxies, timeout=10)

                if response.status_code != 200:
                    logger.warning(f"Не удалось получить страницу Nitter для {username}, код {response.status_code}")
                    continue  # Пробуем следующий инстанс

                # Парсим HTML
                soup = BeautifulSoup(response.text, "html.parser")

                # Nitter имеет более стабильную структуру HTML
                timeline = soup.select(".timeline-item")
                if not timeline:
                    logger.info(f"Твиты не найдены на Nitter для {username}")
                    continue  # Пробуем следующий инстанс

                # Берем первый твит
                tweet = timeline[0]

                # Извлекаем ID твита
                link = tweet.select_one(".tweet-link")
                if not link or "href" not in link.attrs:
                    continue  # Пробуем следующий инстанс

                href = link["href"]
                match = re.search(r'/status/(\d+)', href)
                if not match:
                    continue  # Пробуем следующий инстанс

                tweet_id = match.group(1)

                # Извлекаем текст твита
                content = tweet.select_one(".tweet-content")
                tweet_text = content.get_text(strip=True) if content else "[Новый твит]"

                # Ограничиваем длину текста
                if len(tweet_text) > 280:
                    tweet_text = tweet_text[:277] + "..."

                # Создаем URL для оригинального твита на Twitter
                tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

                result = (tweet_id, {"text": tweet_text, "url": tweet_url})
                self.set_cache(cache_key, result)
                return result

            except Exception as e:
                logger.error(f"Ошибка при получении твита через Nitter для {username}: {e}")
                # Продолжаем цикл для следующего инстанса

        # Если все инстансы не сработали
        return None, None

    # Метод получения твитов через TweetDeck
    def get_latest_tweet_tweetdeck(self, username, use_proxies=False):
        """Получает последний твит пользователя через TweetDeck"""
        cache_key = self.get_cache_key("tweetdeck", username)
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached

        url = f"https://tweetdeck.twitter.com/"

        # TweetDeck требует более аутентичных заголовков
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Referer": "https://twitter.com/",
            "Origin": "https://twitter.com",
            "sec-ch-ua": '"Chromium";v="96", "Google Chrome";v="96"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        try:
            # Используем прокси, если включено
            proxies = get_random_proxy() if use_proxies else None

            # Сначала загружаем TweetDeck для получения необходимых cookie
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Не удалось получить доступ к TweetDeck, код {response.status_code}")
                return None, None

            # Затем получаем данные пользователя через TweetDeck API
            tweetdeck_api_url = f"https://api.tweetdeck.com/1.1/statuses/user_timeline.json"
            params = {
                "screen_name": username,
                "count": 1,
                "include_entities": "false",
                "include_ext_alt_text": "false",
                "include_reply_count": "false",
            }

            api_response = self.session.get(tweetdeck_api_url, headers=headers, params=params, proxies=proxies,
                                            timeout=15)

            if api_response.status_code != 200:
                logger.warning(
                    f"Не удалось получить данные через TweetDeck API для {username}, код {api_response.status_code}")
                return None, None

            tweets = api_response.json()
            if not tweets or len(tweets) == 0:
                return None, None

            latest = tweets[0]
            tweet_id = latest.get("id_str")
            tweet_text = latest.get("text", "[Новый твит]")
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

            result = (tweet_id, {"text": tweet_text, "url": tweet_url})
            self.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Ошибка при получении твита через TweetDeck для {username}: {e}")
            return None, None

    # Асинхронный метод для получения твитов одновременно несколькими методами
    async def get_latest_tweet_multi(self, username, methods=None, use_proxies=False):
        """Пытается получить последний твит разными методами одновременно"""
        await self.init_async_session()

        if not methods:
            methods = ["nitter", "web", "tweetdeck"]

        tasks = []

        # Создаем асинхронные задачи для каждого метода
        for method in methods:
            if method == "nitter":
                tasks.append(asyncio.create_task(self.get_latest_tweet_nitter_async(username, use_proxies)))
            elif method == "web":
                tasks.append(asyncio.create_task(self.get_latest_tweet_web_async(username, use_proxies)))
            elif method == "tweetdeck":
                tasks.append(asyncio.create_task(self.get_latest_tweet_tweetdeck_async(username, use_proxies)))

        # Выполняем все задачи конкурентно и ждем первого успешного результата
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        # Отменяем оставшиеся задачи
        for task in pending:
            task.cancel()

        # Обрабатываем выполненные задачи
        result = None
        for task in done:
            try:
                method_result = task.result()
                if method_result and method_result[0]:  # Если нашли ID твита
                    result = method_result
                    break
            except Exception as e:
                logger.error(f"Ошибка в асинхронной задаче для {username}: {e}")

        return result

    # Асинхронные методы для различных способов получения твитов
    async def get_latest_tweet_web_async(self, username, use_proxies=False):
        """Асинхронная версия метода получения твитов через web"""
        return self.get_latest_tweet_web(username, use_proxies)

    async def get_latest_tweet_nitter_async(self, username, use_proxies=False):
        """Асинхронная версия метода получения твитов через Nitter"""
        return self.get_latest_tweet_nitter(username, use_proxies)

    async def get_latest_tweet_tweetdeck_async(self, username, use_proxies=False):
        """Асинхронная версия метода получения твитов через TweetDeck"""
        return self.get_latest_tweet_tweetdeck(username, use_proxies)


# Многометодная проверка твитов
async def check_tweet_multi_method(username, methods=None, use_proxies=False):
    """Проверяет твиты всеми доступными методами, возвращает первый успешный результат"""
    if not methods:
        methods = ["nitter", "web", "api"]

    twitter_api = TwitterClient(TWITTER_BEARER)
    scrapers = TwitterScrapers()

    user_id = None
    tweet_id = None
    tweet_data = None
    successful_method = None

    # Определяем порядок проверки методов
    for method in methods:
        # Если уже нашли твит, прерываем поиск
        if tweet_id:
            break

        try:
            if method == "api" and TWITTER_BEARER and not twitter_api.rate_limited:
                # Пробуем через официальный API
                user_id, tweet_id, tweet_data = twitter_api.get_latest_tweet(username, use_proxies)
                if tweet_id:
                    successful_method = "api"

            elif method == "nitter":
                # Пробуем через Nitter
                tweet_id, tweet_data = scrapers.get_latest_tweet_nitter(username, use_proxies)
                if tweet_id:
                    successful_method = "nitter"

            elif method == "web":
                # Пробуем через прямой скрапинг
                tweet_id, tweet_data = scrapers.get_latest_tweet_web(username, use_proxies)
                if tweet_id:
                    successful_method = "web"

            elif method == "tweetdeck":
                # Пробуем через TweetDeck
                tweet_id, tweet_data = scrapers.get_latest_tweet_tweetdeck(username, use_proxies)
                if tweet_id:
                    successful_method = "tweetdeck"

            elif method == "multi":
                # Асинхронная проверка всеми методами одновременно
                tweet_id, tweet_data = await scrapers.get_latest_tweet_multi(
                    username, ["nitter", "web", "tweetdeck"], use_proxies)
                if tweet_id:
                    successful_method = "multi"

        except Exception as e:
            logger.error(f"Ошибка при проверке {username} методом {method}: {e}")

    # Закрываем асинхронную сессию
    await scrapers.close_async_session()

    return user_id, tweet_id, tweet_data, successful_method


# Команды бота
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = load_json(SUBSCRIBERS_FILE, [])
    if chat_id not in subs:
        subs.append(chat_id)
        save_json(SUBSCRIBERS_FILE, subs)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")],
        [InlineKeyboardButton("🔍 Проверить твиты", callback_data="check")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

    await update.message.reply_text(
        "👋 Бот мониторинга Twitter!\n\n"
        "Используйте команды:\n"
        "/add <username> - добавить аккаунт\n"
        "/remove <username> - удалить аккаунт\n"
        "/list - список аккаунтов\n"
        "/check - проверить твиты\n"
        "/interval <минуты> - интервал проверки\n"
        "/settings - настройки\n"
        "/proxy - управление прокси\n"
        "/update_nitter - обновить список Nitter-инстансов",
        reply_markup=keyboard
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "list":
        await cmd_list(update, context)
    elif query.data == "check":
        await cmd_check(update, context)
    elif query.data == "settings":
        await cmd_settings(update, context)
    elif query.data == "toggle_proxies":
        await toggle_proxies(update, context)
    elif query.data == "toggle_monitoring":
        await toggle_monitoring(update, context)
    elif query.data.startswith("method_priority:"):
        # Обработка изменения приоритета методов
        method = query.data.split(":", 1)[1]
        await change_method_priority(update, context, method)


async def toggle_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включает/выключает использование прокси"""
    settings = get_settings()
    current = settings.get("use_proxies", False)
    settings["use_proxies"] = not current
    save_json(SETTINGS_FILE, settings)

    status = "✅ включено" if settings["use_proxies"] else "❌ выключено"

    # Проверяем наличие прокси
    proxies = get_proxies()
    proxy_count = len(proxies.get("proxies", []))

    await update.callback_query.edit_message_text(
        f"Использование прокси: {status}\n\n"
        f"Количество прокси: {proxy_count}\n\n"
        "Вернитесь в настройки с помощью /settings",
    )


async def toggle_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включает/выключает мониторинг"""
    settings = get_settings()
    current = settings.get("enabled", True)
    settings["enabled"] = not current
    save_json(SETTINGS_FILE, settings)

    status = "✅ включен" if settings["enabled"] else "❌ выключен"

    await update.callback_query.edit_message_text(
        f"Мониторинг: {status}\n\n"
        "Вернитесь в настройки с помощью /settings",
    )


async def change_method_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, method):
    """Изменяет приоритет методов проверки"""
    settings = get_settings()
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    # Перемещаем выбранный метод в начало списка
    if method in methods:
        methods.remove(method)
    methods.insert(0, method)

    # Сохраняем изменения
    settings["scraper_methods"] = methods
    save_json(SETTINGS_FILE, settings)

    # Показываем настройки
    await cmd_settings(update, context)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает и позволяет изменить настройки бота"""
    settings = get_settings()

    # Получаем текущие настройки
    interval_mins = settings.get("check_interval", DEFAULT_CHECK_INTERVAL) // 60
    enabled = settings.get("enabled", True)
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])
    parallel_checks = settings.get("parallel_checks", 3)
    randomize = settings.get("randomize_intervals", True)

    # Формируем статусы
    enabled_status = "✅ включен" if enabled else "❌ выключен"
    proxies_status = "✅ включено" if use_proxies else "❌ выключено"
    randomize_status = "✅ включено" if randomize else "❌ выключено"

    # Получаем статистику прокси
    proxies = get_proxies()
    proxy_count = len(proxies.get("proxies", []))

    # Получаем статистику Nitter-инстансов
    nitter_instances = settings.get("nitter_instances", [])
    nitter_count = len(nitter_instances)

    # Формируем сообщение
    msg = (
        "⚙️ **Настройки мониторинга**\n\n"
        f"• Мониторинг: {enabled_status}\n"
        f"• Интервал проверки: {interval_mins} мин.\n"
        f"• Случайные интервалы: {randomize_status}\n"
        f"• Одновременные проверки: {parallel_checks}\n"
        f"• Использование прокси: {proxies_status} (доступно: {proxy_count})\n"
        f"• Nitter-инстансы: {nitter_count}\n\n"
        f"• Приоритет методов: {', '.join(methods)}\n\n"
    )

    # Создаем клавиатуру с кнопками настроек
    keyboard = []

    # Кнопки включения/выключения
    keyboard.append([
        InlineKeyboardButton("🔄 Вкл/выкл мониторинг", callback_data="toggle_monitoring"),
        InlineKeyboardButton("🔌 Вкл/выкл прокси", callback_data="toggle_proxies")
    ])

    # Кнопки для изменения приоритета методов
    keyboard.append([
        InlineKeyboardButton("API", callback_data="method_priority:api"),
        InlineKeyboardButton("Nitter", callback_data="method_priority:nitter"),
        InlineKeyboardButton("Web", callback_data="method_priority:web")
    ])

    # Возвращение в главное меню
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="list")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение или отправляем новое
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")


async def cmd_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление прокси-серверами"""
    if not context.args:
        # Показываем список прокси, когда команда вызывается без аргументов
        proxies = get_proxies()
        proxy_list = proxies.get("proxies", [])

        if not proxy_list:
            await update.message.reply_text(
                "⚠️ Список прокси пуст.\n\n"
                "Добавьте прокси командой:\n"
                "/proxy add <ip:port> или <ip:port:user:pass>\n\n"
                "Другие команды:\n"
                "/proxy list - показать список прокси\n"
                "/proxy clear - очистить список прокси"
            )
            return

        # Формируем сообщение со списком прокси (до 20 для краткости)
        msg = f"🔌 Всего прокси: {len(proxy_list)}\n\n"
        for i, proxy in enumerate(proxy_list[:20], 1):
            msg += f"{i}. `{proxy}`\n"

        if len(proxy_list) > 20:
            msg += f"\n... и еще {len(proxy_list) - 20} прокси."

        msg += "\n\nДля добавления используйте:\n/proxy add <ip:port> или <ip:port:user:pass>"

        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    action = context.args[0].lower()

    if action == "add" and len(context.args) > 1:
        proxy = context.args[1]
        proxies = get_proxies()
        proxy_list = proxies.get("proxies", [])

        # Проверяем формат прокси
        if ":" not in proxy:
            await update.message.reply_text("❌ Неверный формат прокси. Используйте ip:port или ip:port:user:pass")
            return

        # Добавляем прокси, если его еще нет в списке
        if proxy not in proxy_list:
            proxy_list.append(proxy)
            proxies["proxies"] = proxy_list
            save_json(PROXIES_FILE, proxies)
            await update.message.reply_text(f"✅ Прокси `{proxy}` добавлен. Всего: {len(proxy_list)}",
                                            parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Этот прокси уже добавлен")

    elif action == "list":
        # Вместо рекурсивного вызова показываем список напрямую
        proxies = get_proxies()
        proxy_list = proxies.get("proxies", [])

        if not proxy_list:
            await update.message.reply_text("Список прокси пуст.")
            return

        msg = f"🔌 Всего прокси: {len(proxy_list)}\n\n"
        for i, proxy in enumerate(proxy_list[:20], 1):
            msg += f"{i}. `{proxy}`\n"

        if len(proxy_list) > 20:
            msg += f"\n... и еще {len(proxy_list) - 20} прокси."

        await update.message.reply_text(msg, parse_mode="Markdown")

    elif action == "clear":
        save_json(PROXIES_FILE, {"proxies": []})
        await update.message.reply_text("✅ Список прокси очищен")

    else:
        await update.message.reply_text(
            "❓ Неизвестная команда. Используйте:\n"
            "/proxy add <ip:port> - добавить прокси\n"
            "/proxy list - показать список прокси\n"
            "/proxy clear - очистить список прокси"
        )


async def cmd_update_nitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет список Nitter-инстансов"""
    message = await update.message.reply_text("🔍 Проверка доступных Nitter-инстансов...")

    try:
        instances = await update_nitter_instances()

        if instances:
            await message.edit_text(
                f"✅ Найдено {len(instances)} рабочих Nitter-инстансов:\n\n" +
                "\n".join(f"• {instance}" for instance in instances)
            )
        else:
            await message.edit_text(
                "❌ Не найдено работающих Nitter-инстансов. Будет использоваться прямой скрапинг Twitter."
            )
    except Exception as e:
        await message.edit_text(f"❌ Ошибка при обновлении: {str(e)}")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Использование: /add <username>")

    username = context.args[0].lstrip("@")
    accounts = init_accounts()

    if username.lower() in accounts:
        return await update.message.reply_text(f"@{username} уже добавлен.")

    message = await update.message.reply_text(f"Проверяем @{username}...")

    # Получаем настройки
    settings = get_settings()
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    # Используем мультиметодную проверку
    user_id, tweet_id, tweet_data, method = await check_tweet_multi_method(
        username, methods, use_proxies
    )

    # Обрабатываем ограничения API
    twitter_api = TwitterClient(TWITTER_BEARER)
    if twitter_api.rate_limited and "api" in methods:
        reset_time = datetime.fromtimestamp(twitter_api.rate_limit_reset).strftime("%H:%M:%S")
        methods = [m for m in methods if m != "api"]  # Удаляем API из методов

        if not methods:
            await message.edit_text(f"⚠️ API Twitter в лимите до {reset_time}. Попробуйте позже.")
            return

    if not tweet_id:
        return await message.edit_text(f"❌ Не удалось найти аккаунт @{username} или получить его твиты.")

    # Добавляем аккаунт
    accounts[username.lower()] = {
        "username": username,
        "user_id": user_id,  # Может быть None
        "added_at": datetime.now().isoformat(),
        "last_check": datetime.now().isoformat(),
        "last_tweet_id": tweet_id,
        "check_count": 1,
        "success_rate": 100.0,
        "fail_count": 0,
        "check_method": method,
        "priority": 1.0
    }
    save_json(ACCOUNTS_FILE, accounts)

    # Сообщаем о результате
    result = f"✅ Добавлен @{username}\nПоследний твит: {tweet_id}\nМетод проверки: {method}"
    await message.edit_text(result)

    # Отправляем твит, если есть данные
    if tweet_data:
        tweet_msg = f"🐦 @{username}:\n\n{tweet_data['text']}\n\n{tweet_data['url']}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=tweet_msg)


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Использование: /remove <username>")

    username = context.args[0].lstrip("@")
    accounts = init_accounts()

    if username.lower() not in accounts:
        return await update.message.reply_text(f"@{username} не найден в списке.")

    del accounts[username.lower()]
    save_json(ACCOUNTS_FILE, accounts)
    await update.message.reply_text(f"✅ Удалён @{username}.")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    msg = f"⚙️ Настройки:\n• Интервал проверки: {interval_mins} мин.\n• Мониторинг: {status}\n\n"
    msg += f"📋 Аккаунты ({len(accounts)}):\n"

    for username, data in sorted(accounts.items(), key=lambda x: x[1].get("priority", 1.0), reverse=True):
        display_name = data.get('username', username)
        last_check = data.get("last_check", "никогда")
        tweet_id = data.get("last_tweet_id", "нет")
        method = data.get("check_method", "unknown")
        success_rate = data.get("success_rate", 100.0)

        if last_check != "никогда":
            try:
                check_dt = datetime.fromisoformat(last_check)
                last_check = check_dt.strftime("%Y-%m-%d %H:%M")
            except:
                last_check = "недавно"

        msg += f"• @{display_name} (ID: {tweet_id}, {success_rate:.0f}%, метод: {method}, проверка: {last_check})\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Проверить твиты", callback_data="check")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ])

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, reply_markup=keyboard)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(update, 'callback_query') and update.callback_query:
        message = await update.callback_query.edit_message_text("Проверяем твиты...")
    else:
        message = await update.message.reply_text("Проверяем твиты...")

    accounts = init_accounts()

    if not accounts:
        return await message.edit_text(
            "Список пуст. Добавьте аккаунты с помощью команды /add <username>"
        )

    settings = get_settings()
    use_proxies = settings.get("use_proxies", False)
    methods = settings.get("scraper_methods", ["nitter", "web", "api"])

    results = []
    new_tweets = []
    found_tweets = []  # Список для хранения всех найденных твитов
    accounts_updated = False

    # Проверяем каждый аккаунт
    for username, account in accounts.items():
        display_name = account.get('username', username)
        last_id = account.get('last_tweet_id')

        # Обновляем время проверки
        account['last_check'] = datetime.now().isoformat()
        account['check_count'] = account.get('check_count', 0) + 1
        accounts_updated = True

        try:
            # Используем мультиметодную проверку
            user_id, tweet_id, tweet_data, method = await check_tweet_multi_method(
                display_name, methods, use_proxies
            )

            # Обновляем ID пользователя, если получили новый
            if user_id and not account.get('user_id'):
                account['user_id'] = user_id
                accounts_updated = True

            # Если не нашли твит
            if not tweet_id:
                # Увеличиваем счетчик неудач
                account['fail_count'] = account.get('fail_count', 0) + 1

                # Обновляем процент успеха
                total_checks = account.get('check_count', 1)
                fail_count = account.get('fail_count', 0)
                account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

                # Если есть сохраненный твит, показываем его
                if last_id:
                    results.append(f"❓ @{display_name}: твиты не найдены, последний известный ID: {last_id}")
                else:
                    results.append(f"❓ @{display_name}: твиты не найдены")
                continue

            # Сбрасываем счетчик неудач при успехе
            if account.get('fail_count', 0) > 0:
                account['fail_count'] = max(0, account.get('fail_count', 0) - 1)

            # Обновляем процент успеха
            total_checks = account.get('check_count', 1)
            fail_count = account.get('fail_count', 0)
            account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

            # Обновляем метод проверки
            account['check_method'] = method

            # Сохраняем информацию о найденном твите в любом случае
            if tweet_data:
                found_tweets.append({
                    'username': display_name,
                    'tweet_id': tweet_id,
                    'data': tweet_data,
                    'is_new': tweet_id != last_id
                })

            # Если это первая проверка или новый твит
            if not last_id:
                account['last_tweet_id'] = tweet_id
                accounts_updated = True
                results.append(f"📝 @{display_name}: сохранен ID твита {tweet_id}")
            elif tweet_id != last_id:
                # Нашли новый твит!
                account['last_tweet_id'] = tweet_id
                accounts_updated = True
                new_tweets.append({
                    'username': display_name,
                    'tweet_id': tweet_id,
                    'data': tweet_data
                })
                results.append(f"✅ @{display_name}: найден новый твит {tweet_id} (метод: {method})")
            else:
                results.append(f"🔄 @{display_name}: нет новых твитов (метод: {method})")

        except Exception as e:
            logger.error(f"Ошибка при проверке @{display_name}: {e}")
            traceback.print_exc()

            # Увеличиваем счетчик неудач
            account['fail_count'] = account.get('fail_count', 0) + 1

            # Обновляем процент успеха
            total_checks = account.get('check_count', 1)
            fail_count = account.get('fail_count', 0)
            account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

            results.append(f"❌ @{display_name}: ошибка - {str(e)[:50]}")

    # Сохраняем обновленные данные
    if accounts_updated:
        save_json(ACCOUNTS_FILE, accounts)

    # Проверяем состояние API и Nitter
    twitter_api = TwitterClient(TWITTER_BEARER)
    api_limited = twitter_api.rate_limited
    settings = get_settings()
    nitter_instances = settings.get("nitter_instances", [])

    # Формируем сообщение о статусе
    status_msg = ""
    if api_limited and "api" in methods:
        reset_time = datetime.fromtimestamp(twitter_api.rate_limit_reset).strftime("%H:%M:%S")
        status_msg += f"⚠️ Twitter API в лимите до {reset_time}. Используются альтернативные методы.\n\n"

    if not nitter_instances and "nitter" in methods:
        status_msg += "⚠️ Все Nitter-инстансы недоступны, используется прямой скрапинг Twitter.\n\n"

    # Показываем результаты
    if new_tweets:
        # Сначала отправляем сводку
        await message.edit_text(f"{status_msg}✅ Найдено {len(new_tweets)} новых твитов!")

        # Затем отправляем каждый твит отдельным сообщением
        for tweet in new_tweets:
            tweet_msg = f"🐦 @{tweet['username']}:\n\n{tweet['data']['text']}\n\n{tweet['data']['url']}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=tweet_msg)
    else:
        # Даже если нет новых твитов, показываем последние известные
        if found_tweets:
            # Выбираем первый твит для показа
            first_tweet = found_tweets[0]
            tweet_msg = (
                    f"{status_msg}🔍 Новых твитов не найдено.\n\n"
                    f"📊 Результаты проверки:\n"
                    + "\n".join(results)
                    + f"\n\n📱 Последний твит @{first_tweet['username']}:\n"
                      f"{first_tweet['data']['text']}\n\n"
                      f"🔗 {first_tweet['data']['url']}"
            )

            # Создаем клавиатуру с кнопками
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить снова", callback_data="check"),
                InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")
            ]])

            await message.edit_text(tweet_msg, reply_markup=keyboard, disable_web_page_preview=False)
        else:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить снова", callback_data="check"),
                InlineKeyboardButton("📋 Список аккаунтов", callback_data="list")
            ]])
            await message.edit_text(f"{status_msg}🔍 Твиты не найдены.\n\n" + "\n".join(results), reply_markup=keyboard)


async def cmd_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        settings = get_settings()
        current_mins = settings["check_interval"] // 60
        return await update.message.reply_text(
            f"Текущий интервал проверки: {current_mins} мин.\n"
            f"Для изменения: /interval <минуты>"
        )

    try:
        mins = int(context.args[0])
        if mins < 1:
            return await update.message.reply_text("Интервал должен быть не менее 1 минуты.")
        if mins > 1440:  # 24 часа
            return await update.message.reply_text("Интервал должен быть не более 1440 минут (24 часа).")

        settings = update_setting("check_interval", mins * 60)
        await update.message.reply_text(f"✅ Интервал проверки установлен на {mins} мин.")
    except ValueError:
        await update.message.reply_text("Использование: /interval <минуты>")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику работы бота"""
    accounts = init_accounts()

    if not accounts:
        return await update.message.reply_text("Аккаунты не добавлены")

    # Собираем статистику
    total_checks = sum(acct.get("check_count", 0) for acct in accounts.values())
    total_fails = sum(acct.get("fail_count", 0) for acct in accounts.values())
    success_rate = 100.0 * (total_checks - total_fails) / max(1, total_checks)

    # Методы проверки
    methods = {}
    for account in accounts.values():
        method = account.get("check_method")
        if method:
            methods[method] = methods.get(method, 0) + 1

    # Аккаунты с наибольшим процентом успешных проверок
    most_reliable = sorted(
        [(username, data.get("success_rate", 0)) for username, data in accounts.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Аккаунты с наименьшим процентом успешных проверок
    least_reliable = sorted(
        [(username, data.get("success_rate", 0)) for username, data in accounts.items()],
        key=lambda x: x[1]
    )[:5]

    # Формируем сообщение
    msg = (
        "📊 **Статистика мониторинга**\n\n"
        f"• Всего аккаунтов: {len(accounts)}\n"
        f"• Всего проверок: {total_checks}\n"
        f"• Успешных проверок: {total_checks - total_fails} ({success_rate:.1f}%)\n\n"

        "**Методы проверки:**\n"
    )

    # Добавляем методы проверки
    for method, count in methods.items():
        percent = 100.0 * count / len(accounts)
        msg += f"• {method}: {count} ({percent:.1f}%)\n"

    # Добавляем надежные аккаунты
    msg += "\n**Самые надежные аккаунты:**\n"
    for username, rate in most_reliable:
        msg += f"• @{accounts[username].get('username', username)}: {rate:.1f}%\n"

    # Добавляем проблемные аккаунты
    msg += "\n**Проблемные аккаунты:**\n"
    for username, rate in least_reliable:
        msg += f"• @{accounts[username].get('username', username)}: {rate:.1f}%\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


# Глобальная переменная для фоновой задачи
background_task = None


async def background_check(app):
    """Фоновая проверка аккаунтов"""
    global background_task
    background_task = asyncio.current_task()

    await asyncio.sleep(10)  # Начальная задержка

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

            # Сортируем аккаунты по времени последней проверки и приоритету
            sorted_accounts = sorted(
                accounts.items(),
                key=lambda x: (
                    datetime.fromisoformat(x[1].get("last_check", "2000-01-01T00:00:00")),
                    -x[1].get("priority", 1.0)
                )
            )

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
                for username, account in batch:
                    if asyncio.current_task().cancelled():
                        break

                    display_name = account.get('username', username)
                    tasks.append(process_account(app, subs, accounts, display_name, account, methods, use_proxies))

                # Запускаем все задачи параллельно
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Ошибка в параллельной проверке: {result}")
                        elif result:  # Если был обновлен аккаунт
                            accounts_updated = True

                # Небольшая задержка между группами
                await asyncio.sleep(3)

            # Сохраняем обновленные данные
            if accounts_updated:
                save_json(ACCOUNTS_FILE, accounts)

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


async def process_account(app, subs, accounts, username, account, methods, use_proxies):
    """Обрабатывает один аккаунт и отправляет уведомления при новых твитах"""
    try:
        # Обновляем время проверки
        account['last_check'] = datetime.now().isoformat()
        account['check_count'] = account.get('check_count', 0) + 1

        # Получаем последний известный твит
        last_id = account.get('last_tweet_id')

        # Используем мультиметодную проверку
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

            # Обновляем процент успеха
            total_checks = account.get('check_count', 1)
            fail_count = account.get('fail_count', 0)
            account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

            # Уменьшаем приоритет проблемных аккаунтов
            if account.get('fail_count', 0) > 3:
                account['priority'] = max(0.1, account.get('priority', 1.0) * 0.9)

            logger.info(f"Аккаунт @{username}: твиты не найдены (методы: {methods})")
            return True

        # Сбрасываем счетчик неудач при успехе и восстанавливаем приоритет
        if account.get('fail_count', 0) > 0:
            account['fail_count'] = max(0, account.get('fail_count', 0) - 1)

        if account.get('priority', 1.0) < 1.0:
            account['priority'] = min(1.0, account.get('priority', 1.0) * 1.1)

        # Обновляем процент успеха
        total_checks = account.get('check_count', 1)
        fail_count = account.get('fail_count', 0)
        account['success_rate'] = 100 * (total_checks - fail_count) / total_checks

        # Обновляем метод проверки
        account['check_method'] = method

        # Если это первая проверка
        if not last_id:
            account['last_tweet_id'] = tweet_id
            logger.info(f"Аккаунт @{username}: первая проверка, сохранен ID {tweet_id}")
            return True

        # Если нашли новый твит
        elif tweet_id != last_id:
            account['last_tweet_id'] = tweet_id
            logger.info(f"Аккаунт @{username}: новый твит {tweet_id}, отправляем уведомления")

            # Отправляем уведомления всем подписчикам
            if tweet_data:
                tweet_msg = f"🐦 @{username}:\n\n{tweet_data['text']}\n\n{tweet_data['url']}"
                for chat_id in subs:
                    try:
                        await app.bot.send_message(chat_id=chat_id, text=tweet_msg)
                        await asyncio.sleep(0.5)  # Небольшая задержка
                    except Exception as e:
                        logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}")
            return True
        else:
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
    global background_task

    # Инициализируем команды
    await app.bot.set_my_commands([
        BotCommand("start", "Начало работы"),
        BotCommand("add", "Добавить аккаунт"),
        BotCommand("remove", "Удалить аккаунт"),
        BotCommand("list", "Список аккаунтов"),
        BotCommand("check", "Проверить твиты"),
        BotCommand("interval", "Интервал проверки"),
        BotCommand("settings", "Настройки бота"),
        BotCommand("proxy", "Управление прокси"),
        BotCommand("stats", "Статистика мониторинга"),
        BotCommand("update_nitter", "Обновить Nitter-инстансы")
    ])

    # Инициализируем данные
    init_accounts()

    # Создаем файл прокси, если не существует
    if not os.path.exists(PROXIES_FILE):
        save_json(PROXIES_FILE, {"proxies": []})

    # Обновляем список работающих Nitter-инстансов
    try:
        logger.info("Обновление списка Nitter-инстансов...")
        await update_nitter_instances()
    except Exception as e:
        logger.error(f"Ошибка при обновлении Nitter-инстансов: {e}")

    # Запускаем фоновую задачу
    background_task = asyncio.create_task(background_check(app))
    logger.info("Бот запущен, фоновая задача активирована")


async def on_shutdown(app):
    """Вызывается при остановке бота"""
    global background_task
    if background_task and not background_task.cancelled():
        logger.info("Останавливаем фоновую задачу...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        logger.info("Фоновая задача остановлена")

    # Закрываем все асинхронные сессии
    scrapers = TwitterScrapers()
    await scrapers.close_async_session()


def main():
    # Проверяем наличие токена
    if not TG_TOKEN:
        logger.error("TG_TOKEN не указан в .env файле")
        return

    # Создаем файлы по умолчанию
    for path, default in [
        (SUBSCRIBERS_FILE, []),
        (SETTINGS_FILE, {
            "check_interval": DEFAULT_CHECK_INTERVAL,
            "enabled": True,
            "use_proxies": False,
            "scraper_methods": ["nitter", "web", "api"],
            "max_retries": 3,
            "cache_expiry": 3600,
            "randomize_intervals": True,
            "min_interval_factor": 0.8,
            "max_interval_factor": 1.2,
            "parallel_checks": 3,
            "nitter_instances": []
        })
    ]:
        if not os.path.exists(path):
            save_json(path, default)

    # Создаем и настраиваем приложение
    app = ApplicationBuilder().token(TG_TOKEN).post_init(on_startup).post_shutdown(on_shutdown).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("interval", cmd_interval))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("proxy", cmd_proxy))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("update_nitter", cmd_update_nitter))

    # Обработчик для кнопок
    app.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    settings = get_settings()
    interval_mins = settings["check_interval"] // 60
    logger.info(f"🚀 Бот запущен, интервал проверки: {interval_mins} мин.")
    app.run_polling()


if __name__ == "__main__":
    main()
