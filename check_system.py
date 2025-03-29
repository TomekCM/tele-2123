import os
import subprocess
import sqlite3
import psutil
import sys

def check_python_processes():
    """Проверяет запущенные процессы Python и их аргументы"""
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 1:
                    script_name = cmdline[1]
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'script': os.path.basename(script_name),
                        'command': ' '.join(cmdline)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return python_processes

def check_database():
    """Проверяет состояние базы данных"""
    try:
        conn = sqlite3.connect('messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем общее количество сообщений
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        # Проверяем ожидающие отправки сообщения
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_replied = 1 AND telegram_sent = 0")
        pending_messages = cursor.fetchone()[0]
        
        # Проверяем последние сообщения
        cursor.execute("""
        SELECT id, user_id, timestamp, is_replied, telegram_sent 
        FROM messages 
        ORDER BY id DESC 
        LIMIT 5
        """)
        recent_messages = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_messages': total_messages,
            'pending_messages': pending_messages,
            'recent_messages': recent_messages
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == 'kill':
        subprocess.run(['taskkill', '/f', '/im', 'python.exe'], capture_output=True)
        print("Все процессы Python остановлены.")
        return
    
    # Проверяем процессы
    processes = check_python_processes()
    print(f"Найдено {len(processes)} процессов Python:")
    for proc in processes:
        print(f"PID: {proc['pid']}, Скрипт: {proc['script']}")
        print(f"  Команда: {proc['command']}")
        print()
    
    # Проверяем базу данных
    db_info = check_database()
    if 'error' in db_info:
        print(f"Ошибка проверки базы данных: {db_info['error']}")
    else:
        print(f"Всего сообщений в базе: {db_info['total_messages']}")
        print(f"Ожидает отправки: {db_info['pending_messages']}")
        
        print("\nПоследние сообщения:")
        for msg in db_info['recent_messages']:
            status = 'Отправлено' if msg['telegram_sent'] == 1 else 'Не отправлено'
            replied = 'Ответ' if msg['is_replied'] == 1 else 'Входящее'
            print(f"ID: {msg['id']}, Пользователь: {msg['user_id']}, Время: {msg['timestamp']}, Тип: {replied}, Статус: {status}")
    
    # Предлагаем остановить процессы
    if processes:
        print("\nДля остановки всех процессов Python, запустите: python check_system.py kill")

if __name__ == "__main__":
    main()