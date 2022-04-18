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
TELEGRAM_RETRY_TIME = 600

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
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к эндпоинту: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка при запросе к эндпоинту: {response.reason}')
        raise exceptions.HTTPStatusCodeError(
            f'Ошибка при запросе к эндпоинту: {response.reason}'
        )
    return response.json()


def check_response(response):
    """Проверяет корректность объектов response и homeworks в ответе API."""
    if not isinstance(response, Dict):
        raise TypeError('Ошибка: объект response не является словарем')
    if 'homeworks' not in response.keys():
        raise KeyError('Ошибка: объект response не содержит ключа homeworks')
    if not isinstance(response['homeworks'], List):
        raise TypeError('Ошибка: объект homeworks не является словарем')
    return response['homeworks']


def parse_status(homework):
    """Получает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError(
            'Ошибка: объект homework не содержит ключа homework_name'
        )
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise exceptions.HomeworkStatusError(
            f'Получен неизвестный статус {homework_status}'
            f' домашней работы {homework_name}!'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    result = True
    tokens_to_check = ('TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'PRACTICUM_TOKEN')
    for token in tokens_to_check:
        if globals()[token] is None:
            result = False
            logging.critical(
                f'Отсутствует переменная окружения {token}'
            )
    return result


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Ошибка в переменных окружения. Программа остановлена.'
        )
        raise exceptions.CheckTokensError(
            'Ошибка в переменных окружения. Программа остановлена.'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    message_error_send = False
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', None)
            if current_timestamp is None:
                current_timestamp = int(time.time())
            homeworks = check_response(response)
            if len(homeworks) == 0:
                message = 'Статусы домашних работ пока не изменились'
                send_message(message)
            for homework in homeworks:
                hw_status = parse_status(homework)
                send_message(bot, hw_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if not message_error_send:
                send_message(bot, message)
                message_error_send = True
        finally:
            time.sleep(TELEGRAM_RETRY_TIME)


if __name__ == '__main__':
    main()
