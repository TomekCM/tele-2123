import requests
import sqlite3
import datetime
import sys
import os

# Ваш токен бота
TOKEN = "7653820469:AAHCZ_BGU9CDzCiC8i86Lvwz6Eua2S0f68U"

def print_separator(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)

def test_telegram_connection():
    print_separator("ПРОВЕРКА СОЕДИНЕНИЯ С TELEGRAM API")
    
    try:
        # Проверяем базовое соединение с API Telegram
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        print(f"Статус ответа: {response.status_code}")
        print(f"Ответ API: {response.text[:200]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("✅ Соединение с Telegram API успешно установлено!")
                print(f"   Имя бота: {data['result']['first_name']}")
                print(f"   Username: @{data['result']['username']}")
                return True
            else:
                print(f"❌ API вернул ошибку: {data.get('description')}")
        else:
            print(f"❌ Ошибка соединения с API. Код статуса: {response.status_code}")
        
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке соединения: {e}")
        return False

def check_pending_messages():
    print_separator("ПРОВЕРКА ОЖИДАЮЩИХ СООБЩЕНИЙ")
    
    try:
        conn = sqlite3.connect('messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем сообщения ожидающие отправки
        cursor.execute(
            """SELECT id, user_id, reply_text, timestamp 
               FROM messages 
               WHERE is_replied = 1 AND telegram_sent = 0
               ORDER BY timestamp DESC
               LIMIT 10"""
        )
        
        messages = cursor.fetchall()
        
        if not messages:
            print("Нет сообщений ожидающих отправки")
            
            # Проверим, есть ли вообще исходящие сообщения
            cursor.execute(
                """SELECT COUNT(*) as count 
                   FROM messages 
                   WHERE is_replied = 1"""
            )
            
            count = cursor.fetchone()['count']
            print(f"Всего исходящих сообщений в базе: {count}")
            
            if count > 0:
                # Проверим последние исходящие сообщения
                cursor.execute(
                    """SELECT id, user_id, reply_text, telegram_sent, timestamp 
                       FROM messages 
                       WHERE is_replied = 1
                       ORDER BY timestamp DESC
                       LIMIT 3"""
                )
                
                print("\nПоследние исходящие сообщения:")
                for msg in cursor.fetchall():
                    status = "✅ Отправлено" if msg['telegram_sent'] == 1 else "❌ Не отправлено"
                    print(f"ID: {msg['id']}, Пользователь: {msg['user_id']}")
                    print(f"Текст: {msg['reply_text']}")
                    print(f"Время: {msg['timestamp']}")
                    print(f"Статус: {status}")
                    print("-" * 30)
            
            # Создадим тестовое сообщение если нет ни одного
            if count == 0:
                print("\nСоздание тестового сообщения...")
                choice = input("Создать тестовое сообщение для отправки? (y/n): ")
                if choice.lower() == 'y':
                    return create_test_message()
        else:
            print(f"Найдено {len(messages)} сообщений ожидающих отправки:")
            
            for msg in messages:
                print(f"ID: {msg['id']}, Пользователь: {msg['user_id']}")
                print(f"Текст: {msg['reply_text']}")
                print(f"Время: {msg['timestamp']}")
                print("-" * 30)
            
            # Спросим, нужно ли отправить сообщение напрямую
            choice = input("\nОтправить первое сообщение напрямую через API? (y/n): ")
            if choice.lower() == 'y':
                return send_message_directly(messages[0])
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке сообщений: {e}")
        return False

def create_test_message():
    try:
        # Проверим, есть ли пользователи в базе
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT user_id FROM messages LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("❌ Нет пользователей в базе данных для отправки тестового сообщения")
            user_id = input("Введите ID пользователя Telegram для отправки тестового сообщения: ")
            if not user_id.isdigit():
                print("❌ Неверный ID пользователя")
                return False
            user_id = int(user_id)
        else:
            user_id = result[0]
        
        # Создаем тестовое сообщение
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_message = f"Тестовое сообщение отправлено в {timestamp}"
        
        cursor.execute(
            """INSERT INTO messages 
               (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent) 
               VALUES (?, NULL, ?, 1, 1, ?, 0)""",
            (user_id, timestamp, test_message)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Создано тестовое сообщение (ID: {message_id}) для пользователя {user_id}")
        print(f"Текст: {test_message}")
        
        # Попробуем сразу отправить это сообщение
        cursor.execute(
            """SELECT id, user_id, reply_text, timestamp 
               FROM messages 
               WHERE id = ?""",
            (message_id,)
        )
        
        message = cursor.fetchone()
        conn.close()
        
        if message:
            choice = input("\nОтправить это сообщение напрямую через API? (y/n): ")
            if choice.lower() == 'y':
                return send_message_directly(message)
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании тестового сообщения: {e}")
        return False

def send_message_directly(message):
    print_separator("ПРЯМАЯ ОТПРАВКА СООБЩЕНИЯ ЧЕРЕЗ API")
    
    try:
        print(f"Отправка сообщения (ID: {message['id']}) пользователю {message['user_id']}")
        print(f"Текст: {message['reply_text']}")
        
        # Отправляем сообщение напрямую через API
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            'chat_id': message['user_id'],
            'text': message['reply_text']
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("✅ Сообщение успешно отправлено!")
                
                # Обновим флаг в базе данных
                conn = sqlite3.connect('messages.db')
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE messages SET telegram_sent = 1 WHERE id = ?",
                    (message['id'],)
                )
                conn.commit()
                conn.close()
                
                print("✅ Статус сообщения обновлен в базе данных")
                return True
            else:
                print(f"❌ API вернул ошибку: {data.get('description')}")
        else:
            print(f"❌ Ошибка отправки сообщения. Код статуса: {response.status_code}")
            print(f"Ответ: {response.text}")
        
        return False
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}")
        return False

def check_network_proxy():
    print_separator("ПРОВЕРКА СЕТИ И ПРОКСИ")
    
    try:
        # Проверим подключение к интернету
        print("Проверка доступа к интернету...")
        response = requests.get("https://www.google.com", timeout=5)
        print(f"Google.com доступен, статус: {response.status_code}")
        
        # Проверим, используются ли прокси
        print("\nПроверка настроек прокси:")
        http_proxy = os.environ.get('HTTP_PROXY', 'не установлен')
        https_proxy = os.environ.get('HTTPS_PROXY', 'не установлен')
        
        print(f"HTTP_PROXY: {http_proxy}")
        print(f"HTTPS_PROXY: {https_proxy}")
        
        # Проверим блокировку Telegram API
        print("\nПроверка доступа к Telegram API...")
        try:
            response = requests.get("https://api.telegram.org", timeout=5)
            print(f"api.telegram.org доступен, статус: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка доступа к api.telegram.org: {e}")
            print("⚠️ Возможно, у вас заблокирован доступ к Telegram API.")
            print("   Рассмотрите возможность использования VPN или прокси.")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке сети: {e}")
        return False

def check_bot_code():
    print_separator("ПРОВЕРКА КОДА БОТА")
    
    try:
        if not os.path.exists('bot.py'):
            print("❌ Файл bot.py не найден!")
            return False
        
        with open('bot.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Проверим ключевые части кода
        checks = {
            "Глобальный экземпляр бота": "bot = Bot(token=TOKEN)" in code,
            "Функция check_pending_messages": "def check_pending_messages" in code,
            "Поток для проверки сообщений": "message_thread = threading.Thread" in code,
            "Запуск потока до run_polling": "message_thread.start" in code and code.find("message_thread.start") < code.find("run_polling"),
            "Правильный импорт Bot": "from telegram import Update, Bot" in code
        }
        
        # Выведем результаты проверок
        issues_found = False
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            if not result:
                issues_found = True
            print(f"{status} {check_name}")
        
        if issues_found:
            print("\n⚠️ В коде бота найдены проблемы, которые могут препятствовать отправке сообщений.")
            print("   Рекомендуется исправить указанные проблемы и перезапустить бота.")
        else:
            print("\n✅ Код бота выглядит корректно.")
        
        return not issues_found
    except Exception as e:
        print(f"❌ Ошибка при проверке кода бота: {e}")
        return False

def main():
    print("\n" + "=" * 50)
    print(f"РАСШИРЕННАЯ ДИАГНОСТИКА TELEGRAM BOT - {datetime.datetime.now()}")
    print("=" * 50)
    
    # Запускаем проверки
    network_ok = check_network_proxy()
    api_ok = test_telegram_connection()
    code_ok = check_bot_code()
    messages_ok = check_pending_messages()
    
    # Вывод результатов
    print_separator("РЕЗУЛЬТАТЫ ДИАГНОСТИКИ")
    
    results = {
        "Сеть и прокси": network_ok,
        "Соединение с Telegram API": api_ok,
        "Код бота": code_ok,
        "Сообщения в базе данных": messages_ok
    }
    
    issues_found = False
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        if not result:
            issues_found = True
        print(f"{status} {test_name}")
    
    if issues_found:
        print("\n⚠️ Обнаружены проблемы. Пожалуйста, исправьте указанные выше проблемы.")
    else:
        print("\n✅ Все проверки пройдены успешно.")
        print("   Если сообщения всё ещё не отправляются, возможно, проблема связана с")
        print("   взаимодействием компонентов системы или с особенностями вашей сети.")

if __name__ == "__main__":
    main()