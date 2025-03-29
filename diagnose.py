import sqlite3
import os
import json
import sys

def check_database():
    """Проверка структуры и содержимого базы данных"""
    if not os.path.exists('messages.db'):
        print("[ERROR] База данных messages.db не найдена!")
        return False
    
    print("[INFO] База данных найдена, проверяем структуру...")
    
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(messages)")
        columns = cursor.fetchall()
        print(f"[INFO] Структура таблицы messages:")
        for col in columns:
            print(f"    {col[1]} ({col[2]})")
        
        # Проверяем данные
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_count = cursor.fetchone()[0]
        print(f"[INFO] Всего сообщений в базе: {total_count}")
        
        # Проверяем непрочитанные сообщения
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_replied = 1 AND (telegram_sent IS NULL OR telegram_sent = 0)")
        pending_count = cursor.fetchone()[0]
        print(f"[INFO] Сообщений ожидающих отправки: {pending_count}")
        
        # Выводим последние 5 сообщений с ответами
        cursor.execute("""
            SELECT id, user_id, message_text, reply_text, is_replied, telegram_sent
            FROM messages 
            WHERE reply_text IS NOT NULL
            ORDER BY id DESC LIMIT 5
        """)
        
        messages = cursor.fetchall()
        if messages:
            print("[INFO] Последние сообщения с ответами:")
            for msg in messages:
                msg_id, user_id, text, reply, is_replied, sent = msg
                print(f"    ID: {msg_id} | User: {user_id} | Replied: {is_replied} | Sent: {sent}")
                print(f"    Message: {text[:50]}...")
                print(f"    Reply: {reply[:50]}...")
                print("    " + "-"*50)
        else:
            print("[WARNING] Сообщений с ответами не найдено")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка при проверке базы данных: {e}")
        return False

def check_token(token):
    """Проверка валидности токена бота"""
    import requests
    
    print(f"[INFO] Проверяем токен бота...")
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result')
            print(f"[SUCCESS] Токен действителен! Информация о боте:")
            print(f"    Имя: {bot_info.get('first_name')}")
            print(f"    Username: @{bot_info.get('username')}")
            print(f"    ID: {bot_info.get('id')}")
            return True
        else:
            print(f"[ERROR] Ошибка при проверке токена: {data.get('description')}")
            return False
    
    except Exception as e:
        print(f"[ERROR] Не удалось проверить токен: {e}")
        return False

def test_message_send(token, chat_id):
    """Тестирование отправки сообщения напрямую через API"""
    import requests
    
    print(f"[INFO] Пробуем отправить тестовое сообщение пользователю {chat_id}...")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": "Это тестовое сообщение диагностики. Если вы видите его, значит проблема не в API Telegram."
            }
        )
        data = response.json()
        
        if data.get('ok'):
            print(f"[SUCCESS] Тестовое сообщение успешно отправлено!")
            print(f"    Message ID: {data.get('result', {}).get('message_id')}")
            return True
        else:
            print(f"[ERROR] Не удалось отправить тестовое сообщение: {data.get('description')}")
            return False
    
    except Exception as e:
        print(f"[ERROR] Ошибка при отправке тестового сообщения: {e}")
        return False

def check_dependencies():
    """Проверка установленных зависимостей"""
    import pkg_resources
    
    print("[INFO] Проверяем установленные зависимости...")
    
    required = {
        'python-telegram-bot': '20.0',
        'flask': '2.0'
    }
    
    for package, min_version in required.items():
        try:
            installed = pkg_resources.get_distribution(package)
            print(f"    {package}: установлена версия {installed.version} (требуется {min_version}+)")
        except pkg_resources.DistributionNotFound:
            print(f"    [ERROR] {package} не установлен!")

if __name__ == "__main__":
    print("="*60)
    print("ДИАГНОСТИКА СИСТЕМЫ TELEGRAM-БОТА")
    print("="*60)
    
    # Проверка базы данных
    check_database()
    
    print("\n" + "="*60)
    
    # Проверка зависимостей
    check_dependencies()
    
    print("\n" + "="*60)
    
    # Проверка токена
    token = input("\nВведите токен вашего бота (для проверки): ")
    if token and check_token(token):
        # Проверка отправки сообщения
        chat_id = input("\nВведите ваш Telegram Chat ID (для тестовой отправки): ")
        if chat_id:
            test_message_send(token, chat_id)
    
    print("\n" + "="*60)
    print("Диагностика завершена.")