@echo off
echo Запуск всех компонентов системы...

:: Создание виртуального окружения (если нужно)
python -m venv venv
call venv\Scripts\activate.bat

:: Установка зависимостей
pip install python-telegram-bot flask

:: Запуск каждого компонента в новом окне CMD
start cmd /k python bot.py
start cmd /k python server.py
start cmd /k python bot_server_integration.py

echo Все компоненты запущены!