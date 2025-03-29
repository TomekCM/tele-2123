import subprocess
import sys
import time
import os
import signal

def kill_processes():
    """Завершает все существующие процессы Python"""
    if sys.platform.startswith('win'):
        # Windows
        os.system('taskkill /F /IM python.exe /T')
    else:
        # Linux/Mac
        os.system("pkill -f 'python.*bot.py'")
        os.system("pkill -f 'python.*server.py'")
        os.system("pkill -f 'python.*message_sender.py'")
    
    # Даем время на завершение
    time.sleep(3)

def start_all():
    """Запускает все компоненты системы"""
    print("Запуск веб-сервера...")
    server_process = subprocess.Popen([sys.executable, 'server.py'])
    
    # Пауза для инициализации сервера
    time.sleep(3)
    
    print("Запуск основного бота...")
    bot_process = subprocess.Popen([sys.executable, 'bot.py'])
    
    # Пауза для инициализации бота
    time.sleep(3)
    
    print("Запуск отправщика сообщений...")
    sender_process = subprocess.Popen([sys.executable, 'message_sender.py'])
    
    return server_process, bot_process, sender_process

def main():
    print("\n" + "=" * 50)
    print("ЗАПУСК УЛУЧШЕННОЙ СИСТЕМЫ TELEGRAM")
    print("=" * 50)
    
    # Завершаем все существующие процессы
    print("Завершение существующих процессов...")
    kill_processes()
    
    # Запускаем компоненты
    processes = start_all()
    
    print("\n" + "=" * 50)
    print("ВСЕ КОМПОНЕНТЫ ЗАПУЩЕНЫ УСПЕШНО")
    print("=" * 50)
    print("\nНажмите Ctrl+C для завершения всех процессов")
    
    try:
        # Ожидаем, пока пользователь не прервет программу
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        
        # Завершаем все запущенные процессы
        for process in processes:
            if process.poll() is None:  # Если процесс все еще работает
                if sys.platform.startswith('win'):
                    process.terminate()
                else:
                    os.kill(process.pid, signal.SIGTERM)
        
        print("Все процессы завершены")

if __name__ == "__main__":
    main()