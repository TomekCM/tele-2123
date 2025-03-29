#!/bin/bash

# Проверка наличия Python и pip
if ! command -v python3 &> /dev/null
then
    echo "Python 3 не найден. Установите Python 3 для запуска системы"
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install python-telegram-bot flask

# Запуск компонентов системы
echo "Запуск Telegram бота..."
python bot.py &
BOT_PID=$!

echo "Запуск веб-сервера..."
python server.py &
SERVER_PID=$!

echo "Запуск интеграционного сервиса..."
python bot_server_integration.py &
INTEGRATION_PID=$!

echo "Система запущена!"
echo "Telegram бот: PID $BOT_PID"
echo "Веб-сервер: PID $SERVER_PID"
echo "Интеграционный сервис: PID $INTEGRATION_PID"
echo "Для завершения работы нажмите CTRL+C"

# Обработка завершения работы
trap "kill $BOT_PID $SERVER_PID $INTEGRATION_PID; exit" INT TERM
wait