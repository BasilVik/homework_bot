## homework-bot
Чат-бот Telegram для получения информации о статусе код-ревью домашнего задания (Telegram API)

## Технологический стек:
- Python 3
- python-telegram-bot

## Квикстарт:
- Клонируйте репозиторий
- Перейдите в директорию с проектом
- Создайте виртуальное окружение:
```
python -m venv venv
```
- Активируйте виртуальное окружение:
для windows:
```
source venv/Scripts/activate
```
для linux:
```
source venv/bin/activate
```
- Установите зависимости:
```
pip install -r requirements.txt
```
- Создайте файл .env, в котором укажите переменную окружения SECRET_KEY, а так же укажите следующие значения:
- PRACTICUM_TOKEN = <Токен на Яндекс.Практикум>
- TELEGRAM_TOKEN = <Токен телеграм бота>
- TELEGRAM_CHAT_ID = <ID чата, в который будут приходить оповещения>
