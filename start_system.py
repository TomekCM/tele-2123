import subprocess
import sys
import os
import time

def main():
    # Путь к проекту
    project_dir = r"D:\sifilis"
    os.chdir(project_dir)
    print(f"Рабочая директория: {os.getcwd()}")
    
    # Путь к Python - используем тот, который указан в ваших логах
    python_path = r"C:\Users\alexk\AppData\Local\Programs\Python\Python312\python.exe"
    
    # Проверяем, существует ли интерпретатор
    if not os.path.exists(python_path):
        print(f"Интерпретатор Python не найден по пути: {python_path}")
        print("Используем системный Python")
        python_path = sys.executable
    
    print(f"Используется Python: {python_path}")
    
    # Проверяем и устанавливаем зависимости
    try:
        print("Установка необходимых зависимостей...")
        subprocess.run([python_path, "-m", "pip", "install", "python-telegram-bot", "flask"], 
                      check=True)
        print("Зависимости установлены успешно")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при установке зависимостей: {e}")
        print("Продолжаем запуск, возможно зависимости уже установлены")
    
    # Запуск всех компонентов
    processes = []
    
    try:
        print("Запуск Telegram бота...")
        bot_process = subprocess.Popen([python_path, os.path.join(project_dir, "bot.py")],
                                      creationflags=subprocess.CREATE_NEW_CONSOLE)
        processes.append(("Telegram бот", bot_process))
        
        time.sleep(2)
        
        print("Запуск веб-сервера...")
        server_process = subprocess.Popen([python_path, os.path.join(project_dir, "server.py")],
                                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        processes.append(("Веб-сервер", server_process))
        
        time.sleep(2)
        
        print("Запуск интеграционного сервиса...")
        integration_process = subprocess.Popen([python_path, os.path.join(project_dir, "bot_server_integration.py")],
                                              creationflags=subprocess.CREATE_NEW_CONSOLE)
        processes.append(("Интеграционный сервис", integration_process))
        
        print("\nВсе компоненты системы запущены!")
        print("Веб-интерфейс доступен по адресу: http://localhost:5000")
        print("\nДля остановки всех компонентов нажмите Ctrl+C в этом окне")
        
        # Ожидаем нажатия Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки. Завершение всех компонентов...")
    finally:
        # Завершаем все процессы при выходе
        for name, process in processes:
            if process.poll() is None:  # процесс еще работает
                print(f"Остановка {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Принудительное завершение {name}...")
                    process.kill()
        
        print("Все компоненты остановлены")

if __name__ == "__main__":
    main()