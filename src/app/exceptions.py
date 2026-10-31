class CoffeeApiError(Exception):
    """Ошибка при обращении к SampleAPIs Coffee."""


class CoffeeNotFoundError(CoffeeApiError):
    """Ресурс не найден (ожидаемый HTTP 404)."""


class CoffeeTimeoutError(CoffeeApiError):
    """Сервер не ответил за тайм-аут. Для POST результат неизвестен."""
