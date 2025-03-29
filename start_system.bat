@echo off
echo Запуск системы Telegram бота...

echo Остановка текущих процессов Python...
taskkill /f /im python.exe
timeout /t 2

echo Запуск бота получения сообщений...
start cmd /k "title TelegramBot && python bot.py"

echo Ожидание инициализации бота...
timeout /t 5

echo Запуск отправщика сообщений...
start cmd /k "title MessageSender && python message_sender.py"

echo Система запущена!
echo.
echo Для проверки отправки создайте тестовое сообщение через веб-интерфейс.
echo.

pause