import sqlite3
import datetime
import os
import sys
import subprocess
import time

def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    
def check_database():
    print_header("ПРОВЕРКА БАЗЫ ДАННЫХ")
    
    try:
        conn = sqlite3.connect('messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверка ожидающих отправки сообщений
        cursor.execute(
            """SELECT id, user_id, reply_text, timestamp, telegram_sent 
               FROM messages 
               WHERE is_replied = 1 AND telegram_sent = 0
               ORDER BY timestamp ASC"""
        )
        
        pending_messages = cursor.fetchall()
        print(f"Сообщений, ожидающих отправки: {len(pending_messages)}")
        
        if pending_messages:
            print("\nПЕРВЫЕ 5 СООБЩЕНИЙ В ОЧЕРЕДИ:")
            for i, msg in enumerate(pending_messages[:5]):
                print(f"{i+1}. ID: {msg['id']}, User: {msg['user_id']}")
                print(f"   Текст: {msg['reply_text']}")
                print(f"   Время: {msg['timestamp']}")
                print("-" * 30)
                
        # Проверка последних отправленных сообщений
        cursor.execute(
            """SELECT id, user_id, reply_text, timestamp
               FROM messages 
               WHERE is_replied = 1 AND telegram_sent = 1
               ORDER BY timestamp DESC
               LIMIT 5"""
        )
        
        sent_messages = cursor.fetchall()
        print("\nПОСЛЕДНИЕ 5 ОТПРАВЛЕННЫХ СООБЩЕНИЙ:")
        
        if sent_messages:
            for i, msg in enumerate(sent_messages):
                print(f"{i+1}. ID: {msg['id']}, User: {msg['user_id']}")
                print(f"   Текст: {msg['reply_text']}")
                print(f"   Время: {msg['timestamp']}")
                print("-" * 30)
        else:
            print("Отправленные сообщения не найдены")
            
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при проверке базы данных: {e}")
        return False

def check_bot_running():
    print_header("ПРОВЕРКА ПРОЦЕССА БОТА")
    
    try:
        # Проверяем запущен ли бот
        bot_running = False
        
        if sys.platform.startswith('win'):
            # Windows
            result = subprocess.run(['tasklist'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'bot.py' in line.lower():
                    print(f"Бот запущен: {line.strip()}")
                    bot_running = True
                    break
        else:
            # Linux/Mac
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'bot.py' in line.lower():
                    print(f"Бот запущен: {line.strip()}")
                    bot_running = True
                    break
                    
        if not bot_running:
            print("ОШИБКА: Бот не запущен!")
            return False
            
        return True
    except Exception as e:
        print(f"Ошибка при проверке процесса бота: {e}")
        return False

def check_bot_code():
    print_header("ПРОВЕРКА КОДА БОТА")
    
    if not os.path.exists('bot.py'):
        print("ОШИБКА: Файл bot.py не найден!")
        return False
        
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            bot_code = f.read()
            
        # Проверка на наличие кода проверки новых сообщений
        checks = []
        
        if "telegram_sent = 0" in bot_code:
            checks.append("✅ Код содержит проверку telegram_sent = 0")
        else:
            checks.append("❌ Код НЕ содержит проверку telegram_sent = 0")
            
        if "is_replied = 1" in bot_code:
            checks.append("✅ Код содержит проверку is_replied = 1")
        else:
            checks.append("❌ Код НЕ содержит проверку is_replied = 1")
            
        if "while True" in bot_code and "time.sleep" in bot_code:
            checks.append("✅ Код содержит цикл проверки с задержкой")
        else:
            checks.append("❌ Код НЕ содержит цикл проверки с задержкой")
            
        for check in checks:
            print(check)
            
        return all(check.startswith("✅") for check in checks)
    except Exception as e:
        print(f"Ошибка при проверке кода бота: {e}")
        return False

def send_test_message():
    print_header("ОТПРАВКА ТЕСТОВОГО СООБЩЕНИЯ")
    
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Получаем ID первого пользователя
        cursor.execute("SELECT DISTINCT user_id FROM messages LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("ОШИБКА: Нет пользователей в базе!")
            conn.close()
            return False
            
        user_id = result[0]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_text = f"Тестовое сообщение: {timestamp}"
        
        # Добавляем тестовое сообщение с флагом telegram_sent = 0
        cursor.execute(
            """INSERT INTO messages 
               (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent)
               VALUES (?, NULL, ?, 1, 1, ?, 0)""",
            (user_id, timestamp, test_text)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"Отправлено тестовое сообщение для пользователя {user_id}")
        print(f"ID сообщения: {message_id}")
        print(f"Текст: {test_text}")
        print("\nПРОВЕРЬТЕ СВОЙ TELEGRAM В ТЕЧЕНИЕ МИНУТЫ")
        
        # Ждем и проверяем, изменился ли флаг telegram_sent
        print("Ожидание 30 секунд для проверки отправки...")
        time.sleep(30)
        
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_sent FROM messages WHERE id = ?", (message_id,))
        result = cursor.fetchone()
        sent_flag = result[0] if result else None
        conn.close()
        
        if sent_flag == 1:
            print("✅ Сообщение УСПЕШНО отправлено! (telegram_sent = 1)")
            return True
        else:
            print("❌ Сообщение НЕ было отправлено! (telegram_sent = 0)")
            return False
    except Exception as e:
        print(f"Ошибка при отправке тестового сообщения: {e}")
        return False

def fix_bot_code():
    print_header("ИСПРАВЛЕНИЕ БОТА")
    
    try:
        # Создаем резервную копию
        if os.path.exists('bot.py'):
            with open('bot.py', 'r', encoding='utf-8') as f:
                original_code = f.read()
                
            with open('bot.py.backup', 'w', encoding='utf-8') as f:
                f.write(original_code)
                
            print("✅ Создана резервная копия bot.py.backup")
                
        # Проверяем наличие кода проверки
        has_check_code = False
        
        if os.path.exists('bot.py'):
            with open('bot.py', 'r', encoding='utf-8') as f:
                bot_code = f.read()
                has_check_code = "telegram_sent = 0" in bot_code and "is_replied = 1" in bot_code
        
        if has_check_code:
            print("Код проверки сообщений уже существует в bot.py")
            return True
            
        # Добавляем код для проверки и отправки сообщений
        check_code = """
# Функция для проверки и отправки новых сообщений
def check_pending_messages():
    try:
        conn = sqlite3.connect('messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем сообщения, ожидающие отправки
        cursor.execute(
            \"\"\"SELECT * FROM messages 
               WHERE is_replied = 1 AND telegram_sent = 0
               ORDER BY timestamp ASC\"\"\"
        )
        
        messages = cursor.fetchall()
        
        if messages:
            print(f"Найдено {len(messages)} сообщений для отправки")
            
        for msg in messages:
            try:
                # Отправляем сообщение
                if msg['has_media'] == 1 and msg['media_path']:
                    # Отправка медиа
                    file_path = msg['media_path'].lstrip('/')
                    if os.path.exists(file_path):
                        if msg['media_type'] == 'photo':
                            with open(file_path, 'rb') as photo:
                                bot.send_photo(msg['user_id'], photo, caption=msg['reply_text'])
                        elif msg['media_type'] == 'video':
                            with open(file_path, 'rb') as video:
                                bot.send_video(msg['user_id'], video, caption=msg['reply_text'])
                        elif msg['media_type'] == 'audio':
                            with open(file_path, 'rb') as audio:
                                bot.send_audio(msg['user_id'], audio, caption=msg['reply_text'])
                        else:
                            with open(file_path, 'rb') as doc:
                                bot.send_document(msg['user_id'], doc, caption=msg['reply_text'])
                    else:
                        # Если файл не найден, отправляем только текст
                        bot.send_message(msg['user_id'], f"{msg['reply_text']} (файл не найден)")
                else:
                    # Отправка текста
                    bot.send_message(msg['user_id'], msg['reply_text'])
                
                # Обновляем флаг telegram_sent
                cursor.execute(
                    \"\"\"UPDATE messages SET telegram_sent = 1 WHERE id = ?\"\"\",
                    (msg['id'],)
                )
                conn.commit()
                print(f"Отправлено сообщение {msg['id']} пользователю {msg['user_id']}")
                
            except Exception as e:
                print(f"Ошибка при отправке сообщения {msg['id']}: {e}")
                # Если были ошибки, делаем небольшую паузу
                time.sleep(1)
                
        conn.close()
    except Exception as e:
        print(f"Ошибка при проверке сообщений: {e}")

# Запускаем проверку сообщений в отдельном потоке
import threading
import time

def message_checker():
    while True:
        try:
            check_pending_messages()
        except Exception as e:
            print(f"Ошибка в цикле проверки сообщений: {e}")
        time.sleep(5)  # Проверка каждые 5 секунд

# Запускаем поток проверки сообщений
message_thread = threading.Thread(target=message_checker, daemon=True)
message_thread.start()
"""
        
        # Добавляем код в bot.py
        if os.path.exists('bot.py'):
            with open('bot.py', 'a', encoding='utf-8') as f:
                f.write("\n\n" + check_code)
                
            print("✅ Код проверки и отправки сообщений добавлен в bot.py")
            print("⚠️ Требуется перезапуск бота для применения изменений!")
        else:
            print("❌ Файл bot.py не найден!")
            return False
            
        return True
    except Exception as e:
        print(f"Ошибка при исправлении бота: {e}")
        return False

def restart_bot():
    print_header("ПЕРЕЗАПУСК БОТА")
    
    try:
        # Останавливаем бот
        if sys.platform.startswith('win'):
            # Windows
            result = subprocess.run(['tasklist'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'bot.py' in line.lower():
                    pid = line.split()[1]
                    subprocess.run(['taskkill', '/F', '/PID', pid])
                    print(f"Остановлен процесс с PID {pid}")
        else:
            # Linux/Mac
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'bot.py' in line.lower():
                    pid = line.split()[1]
                    subprocess.run(['kill', pid])
                    print(f"Остановлен процесс с PID {pid}")
        
        # Даем процессу время на завершение
        time.sleep(2)
        
        # Запускаем бот заново
        if sys.platform.startswith('win'):
            # Windows
            subprocess.Popen(['python', 'bot.py'], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # Linux/Mac
            subprocess.Popen(['python3', 'bot.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        print("✅ Бот успешно перезапущен")
        print("⚠️ Подождите несколько секунд, чтобы бот инициализировался")
        time.sleep(5)
        
        return True
    except Exception as e:
        print(f"Ошибка при перезапуске бота: {e}")
        return False

def reset_message_flags():
    print_header("СБРОС ФЛАГОВ ОТПРАВКИ")
    
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Сбрасываем флаг telegram_sent для последних сообщений
        cursor.execute(
            """UPDATE messages 
               SET telegram_sent = 0 
               WHERE is_replied = 1 AND telegram_sent = 1 
               AND id > (SELECT MAX(id) - 20 FROM messages)"""
        )
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"Сброшен флаг telegram_sent для {updated} последних сообщений")
        return True
    except Exception as e:
        print(f"Ошибка при сбросе флагов: {e}")
        return False

def main():
    print("=" * 60)
    print("ДИАГНОСТИКА ОТПРАВКИ СООБЩЕНИЙ В TELEGRAM")
    print("=" * 60)
    print("Время запуска:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Выполняем проверки
    db_ok = check_database()
    bot_running = check_bot_running()
    bot_code_ok = check_bot_code()
    
    # Сводка проблем
    issues = []
    
    if not bot_running:
        issues.append("Бот не запущен!")
        
    if not bot_code_ok:
        issues.append("В коде бота отсутствует проверка новых сообщений!")
        
    if issues:
        print("\nВЫЯВЛЕНЫ ПРОБЛЕМЫ:")
        for i, issue in enumerate(issues):
            print(f"{i+1}. {issue}")
            
        print("\nВЫБЕРИТЕ ДЕЙСТВИЕ:")
        print("1. Исправить код бота и перезапустить")
        print("2. Сбросить флаги telegram_sent для последних сообщений")
        print("3. Отправить тестовое сообщение")
        print("4. Выйти")
        
        choice = input("\nВаш выбор (1-4): ")
        
        if choice == '1':
            fix_bot_code()
            restart_bot()
        elif choice == '2':
            reset_message_flags()
        elif choice == '3':
            send_test_message()
    else:
        print("\nНЕ ОБНАРУЖЕНО КРИТИЧЕСКИХ ПРОБЛЕМ.")
        print("\nВЫБЕРИТЕ ДЕЙСТВИЕ:")
        print("1. Отправить тестовое сообщение")
        print("2. Сбросить флаги telegram_sent для последних сообщений")
        print("3. Выйти")
        
        choice = input("\nВаш выбор (1-3): ")
        
        if choice == '1':
            send_test_message()
        elif choice == '2':
            reset_message_flags()

if __name__ == "__main__":
    main()