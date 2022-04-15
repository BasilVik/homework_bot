import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict, List

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN', default='')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', default='')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', default='')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение об изменившемся статусе домашки в чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')
    else:
        logging.info(f'Отправлено сообщение {message}')


def get_api_answer(current_timestamp):
    """Запрос к API для получения списка домашних работ.
    Запрос должен вернуть домашки с измененным статусом за период.
    """
    message_error_send = False
    error_message = 'Ошибка работы программы!'
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к эндпоинту: {error}')
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка при запросе к эндпоинту: {response.reason}')
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
        raise exceptions.HTTPStatusCodeError(error_message)
    return response.json()


def check_response(response):
    """Проверяет корректность объектов response и homeworks в ответе API."""
    message_error_send = False
    error_message = 'Ошибка работы программы!'
    if not isinstance(response, Dict):
        logging.error('Ошибка: объект response не является словарем')
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
        raise TypeError(error_message)
    homeworks = response.get('homeworks', None)
    if homeworks is None:
        logging.error('Ошибка: объект response не содержит ключа homeworks')
        if not message_error_send:
            bot = create_bot()
            send_message(error_message)
            message_error_send = True
        raise KeyError(error_message)
    if not isinstance(homeworks, List):
        logging.error('Ошибка: объект homeworks не является словарем')
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
        raise TypeError(error_message)
    return homeworks


def parse_status(homework):
    """Получает статус конкретной домашней работы."""
    message_error_send = False
    error_message = 'Ошибка работы программы!'
    homework_name = homework.get('homework_name', None)
    if homework_name is None:
        logging.error(
            'Ошибка: объект homework не содержит ключа homework_name'
        )
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
        raise KeyError(error_message)
    homework_status = homework.get('status', None)
    verdict = HOMEWORK_STATUSES.get(homework_status, None)
    if verdict is None:
        message = f'Получен неизвестный статус {homework_status} '
        message = message + f'домашней работы {homework_name}!'
        logging.error(message)
        if not message_error_send:
            bot = create_bot()
            send_message(bot, error_message)
            message_error_send = True
        raise exceptions.HomeworkStatusError(error_message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    result = True
    if PRACTICUM_TOKEN is None:
        result = False
        logging.critical(
            'Отсутствует переменная окружения PRACTICUM_TOKEN'
        )
    if TELEGRAM_TOKEN is None:
        result = False
        logging.critical(
            'Отсутствует переменная окружения TELEGRAM_TOKEN'
        )
    if TELEGRAM_CHAT_ID is None:
        result = False
        logging.critical(
            'Отсутствует переменная окружения TELEGRAM_CHAT_ID'
        )
    return result


# В задании указано, что нужно отправлять в чат все возможные error.
# Для отправки сообщения нужен бот.
# Если передавать созданного единожды в main бота в другие функции,
# где могут быть ошибки (например check_response(response, bot)),
# то сыпятся тесты. Поэтому сделал так. По-другому не придумалось:(
def create_bot():
    """Создает бота, если переменные окружения заданы."""
    if not check_tokens():
        error_msg = 'Ошибка в переменных окружения. Программа остановлена.'
        logging.error(error_msg)
        raise exceptions.CheckTokensError(error_msg)
    return telegram.Bot(token=TELEGRAM_TOKEN)


def main():
    """Основная логика работы бота."""
    message_error_send = False
    bot = create_bot()
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', None)
            if current_timestamp is None:
                current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if not message_error_send:
                send_message(bot, message)
                message_error_send = True
            time.sleep(RETRY_TIME)
        else:
            homeworks = check_response(response)
            if len(homeworks) == 0:
                message = 'Статусы домашних работ пока не изменились'
                send_message(message)
            for homework in homeworks:
                hw_status = parse_status(homework)
                send_message(bot, hw_status)


if __name__ == '__main__':
    main()
