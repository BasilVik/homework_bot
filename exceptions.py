class HTTPStatusCodeError(Exception):
    """Исключение: код ответа отличается от 200."""

    pass


class HomeworkStatusError(Exception):
    """Исключение: получен неизвестный статус домашней работы."""

    pass


class CheckTokensError(Exception):
    """Исключение: ошибка в переменной окружения."""

    pass
