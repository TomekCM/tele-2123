import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info(f"Python версия: {sys.version}")
    
    try:
        import telegram
        logger.info(f"python-telegram-bot версия: {telegram.__version__}")
    except ImportError:
        logger.error("Библиотека telegram не установлена")
        return
        
    try:
        # Пробуем создать бота
        from telegram import Bot
        bot = Bot(token="7653820469:AAHCZ_BGU9CDzCiC8i86Lvwz6Eua2S0f68U")
        logger.info("Бот успешно создан")
        
        # Проверяем подключение к API
        import asyncio
        
        async def test_connection():
            try:
                me = await bot.get_me()
                logger.info(f"Соединение установлено. Имя бота: {me.first_name}")
            except Exception as e:
                logger.error(f"Ошибка при подключении к API: {e}")
        
        # Запускаем тест соединения
        asyncio.run(test_connection())
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации бота: {e}")

if __name__ == "__main__":
    main()