import logging
import sqlite3
import datetime
import os
import requests
import hashlib
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения, если есть .env файл
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Environment variables loaded from .env file")
except ImportError:
    logger.info("python-dotenv not installed, using direct token")

# Bot token from environment variable or hardcoded
TOKEN = os.getenv("TELEGRAM_TOKEN", "7653820469:AAHCZ_BGU9CDzCiC8i86Lvwz6Eua2S0f68U")

# Create a global application instance
application = None

# Directory for media files
UPLOAD_FOLDER = os.getenv("UPLOADS_FOLDER", 'static/uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database initialization
def init_db():
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        message_text TEXT,
        timestamp TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        is_replied INTEGER DEFAULT 0,
        reply_text TEXT,
        telegram_sent INTEGER DEFAULT 0,
        has_media INTEGER DEFAULT 0,
        media_type TEXT,
        media_file_id TEXT,
        media_path TEXT
    )
    ''')
    
    # Create aliases table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aliases (
        user_id INTEGER PRIMARY KEY,
        real_name TEXT,
        alias TEXT NOT NULL,
        created_at TEXT
    )
    ''')
    
    # Create search table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_search (
        id INTEGER PRIMARY KEY,
        message_id INTEGER,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )
    ''')
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    conn.commit()
    conn.close()

# Log whenever a message is saved to the database
def log_message_saved(user_id, message_text, has_media=False, media_type=None):
    """Log whenever a message is saved to the database"""
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        if has_media:
            logger.info(f"Media message ({media_type}) from user {user_id} saved to database. Total messages for this user: {count}")
        else:
            logger.info(f"Text message from user {user_id} saved to database: '{message_text[:30]}...' Total messages: {count}")
    except Exception as e:
        logger.error(f"Failed to log message save: {e}")

# Function to save media files
async def save_media_file(file_id, media_type):
    try:
        # Create filename based on file_id hash
        file_hash = hashlib.md5(file_id.encode()).hexdigest()
        file_extension = {
            'photo': 'jpg',
            'video': 'mp4',
            'document': 'file',
            'voice': 'ogg',
            'audio': 'mp3',
            'sticker': 'webp'
        }.get(media_type, 'bin')
        
        filename = f"{file_hash}.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # If file already exists, just return the path
        if os.path.exists(file_path):
            return f"/{file_path}"
        
        # Download file using Telegram Bot API directly
        api_url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
        response = requests.get(api_url)
        file_info = response.json()
        
        if file_info.get('ok') and 'result' in file_info:
            file_path_on_server = file_info['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path_on_server}"
            
            # Download the file
            file_response = requests.get(download_url)
            if file_response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(file_response.content)
                logger.info(f"File saved: {file_path}")
                return f"/{file_path}"
        
        logger.error(f"Failed to get file from API: {file_info}")
        return None
    except Exception as e:
        logger.error(f"Error saving media file: {e}")
        return None

# /start command handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(
        "Hello! I'm a messenger bot. Send me a message, and the owner will reply to you through their interface."
    )

# Text message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"Received message from user {user.id}: {message_text[:20]}...")
    
    # Save message to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, username, first_name, message_text, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user.id, user.username, user.first_name, message_text, timestamp)
    )
    
    # Add to search index
    message_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO message_search (message_id, user_id, content) VALUES (?, ?, ?)",
        (message_id, user.id, message_text)
    )
    
    conn.commit()
    conn.close()
    
    # Log the message save
    log_message_saved(user.id, message_text)
    
    # No automatic response

# Photo handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = update.message
    
    logger.info(f"Received photo from user {user.id}")
    
    file_id = message.photo[-1].file_id  # Get the largest photo
    caption = message.caption
    
    # Save the file
    file_path = await save_media_file(file_id, 'photo')
    
    # Save to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, has_media, media_type, media_file_id, media_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username, user.first_name, caption, timestamp, 1, 'photo', file_id, file_path)
    )
    
    # Add to search index if there's a caption
    if caption:
        message_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO message_search (message_id, user_id, content) VALUES (?, ?, ?)",
            (message_id, user.id, caption)
        )
    
    conn.commit()
    conn.close()
    
    # Log the message save for a media message
    log_message_saved(user.id, caption if caption else "", has_media=True, media_type='photo')
    
    # No automatic response

# Document handler
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = update.message
    
    logger.info(f"Received document from user {user.id}")
    
    file_id = message.document.file_id
    caption = message.caption
    
    # Save the file
    file_path = await save_media_file(file_id, 'document')
    
    # Save to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, has_media, media_type, media_file_id, media_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username, user.first_name, caption, timestamp, 1, 'document', file_id, file_path)
    )
    
    if caption:
        message_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO message_search (message_id, user_id, content) VALUES (?, ?, ?)",
            (message_id, user.id, caption)
        )
    
    conn.commit()
    conn.close()
    
    # Log the message save for a media message
    log_message_saved(user.id, caption if caption else "", has_media=True, media_type='document')
    
    # No automatic response

# Audio and voice message handler
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = update.message
    
    logger.info(f"Received audio file from user {user.id}")
    
    if message.voice:
        file_id = message.voice.file_id
        media_type = 'voice'
        caption = None
    else:  # audio
        file_id = message.audio.file_id
        media_type = 'audio'
        caption = message.caption
    
    # Save the file
    file_path = await save_media_file(file_id, media_type)
    
    # Save to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, has_media, media_type, media_file_id, media_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username, user.first_name, caption, timestamp, 1, media_type, file_id, file_path)
    )
    
    if caption:
        message_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO message_search (message_id, user_id, content) VALUES (?, ?, ?)",
            (message_id, user.id, caption)
        )
    
    conn.commit()
    conn.close()
    
    # Log the message save for a media message
    log_message_saved(user.id, caption if caption else "", has_media=True, media_type=media_type)
    
    # No automatic response

# Video handler
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = update.message
    
    logger.info(f"Received video from user {user.id}")
    
    file_id = message.video.file_id
    caption = message.caption
    
    # Save the file
    file_path = await save_media_file(file_id, 'video')
    
    # Save to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, has_media, media_type, media_file_id, media_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username, user.first_name, caption, timestamp, 1, 'video', file_id, file_path)
    )
    
    if caption:
        message_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO message_search (message_id, user_id, content) VALUES (?, ?, ?)",
            (message_id, user.id, caption)
        )
    
    conn.commit()
    conn.close()
    
    # Log the message save for a media message
    log_message_saved(user.id, caption if caption else "", has_media=True, media_type='video')
    
    # No automatic response

# New sticker handler
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = update.message
    
    logger.info(f"Received sticker from user {user.id}")
    
    file_id = message.sticker.file_id
    
    # Save the sticker file
    file_path = await save_media_file(file_id, 'sticker')
    
    # Save to database
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, has_media, media_type, media_file_id, media_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username, user.first_name, None, timestamp, 1, 'sticker', file_id, file_path)
    )
    
    conn.commit()
    conn.close()
    
    # Log the message save for a media message
    log_message_saved(user.id, "", has_media=True, media_type='sticker')
    
    # No automatic response

# Main function - ИСПРАВЛЕНО с правильной обработкой исключений и завершения
async def main():
    global application
    
    try:
        # Initialize database
        init_db()
        
        # Create bot application
        logger.info("Initializing bot application...")
        application = Application.builder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Media file handlers
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
        
        # Note: Message sending functionality disabled
        logger.debug("Message sending functionality disabled - using external message sender only")
        
        # Start the bot
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("Bot is running...")
        
        # Keep the program running until manually interrupted
        try:
            # Бесконечный цикл, который можно прервать с помощью Ctrl+C
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received stop signal, shutting down bot...")
        finally:
            # Правильная последовательность остановки
            try:
                logger.info("Stopping updater...")
                await application.updater.stop()
                logger.info("Stopping application...")
                await application.stop()
                logger.info("Shutting down application...")
                await application.shutdown()
                logger.info("Bot shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown sequence: {e}")
    
    except Exception as e:
        logger.error(f"Critical error in main function: {e}")
        # Если произошла ошибка при запуске, убедимся, что всё корректно останавливается
        if 'application' in locals() and application is not None:
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception as shutdown_error:
                logger.error(f"Error during emergency shutdown: {shutdown_error}")
    
    logger.info("Bot process finished")

# Запуск с правильной обработкой ошибок
def run():
    """Run the bot with proper exception handling"""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    run()