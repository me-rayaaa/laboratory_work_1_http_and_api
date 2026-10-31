"""
Создание горячего кофе

POST https://api.sampleapis.com/coffee/hot
Заголовок Content-Type: application/json (requests ставит его сам, если передать json=)

Тело - JSON-объект, все 4 поля обязательные:
- title (str) - название
- description (str) - описание
- ingredients (list[str]) - список ингредиентов
- image (str) - ссылка на картинку

id не передаем, его выдает сервер (максимальный id + 1).

Успешный ответ: 201, в теле созданный напиток вместе с id.
Если какого-то поля нет: 400 и "The data you are sending does not match the existing data object."

Проверили запросами:
- без любого из 4 полей приходит 400
- типы полей сервер не проверяет, например title=5 тоже сохраняется
- DELETE отвечает 200 и {}, а не 204
- после удаления id освобождается и следующий POST получает тот же id
- если записи нет - 404 и {}

Проверяем только у себя в клиенте:
- что в теле POST и PUT есть все 4 поля

Как устроен клиент:
- _request       - отправляет запрос, ловит ошибки сети и тайм-аут, проверяет код ответа
- _request_json  - вызывает _request и проверяет, что в ответе JSON
- публичные методы - только собирают путь и вызывают одно из двух
"""

import requests

from app.exceptions import CoffeeApiError, CoffeeNotFoundError, CoffeeTimeoutError

JsonObject = dict[str, object]

FIELDS = ["title", "description", "ingredients", "image"]
OK_CODES = (200, 201)


def check_payload(payload: JsonObject) -> None:
    for field in FIELDS:
        if field not in payload:
            raise ValueError(f"в напитке нет поля {field}")


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://api.sampleapis.com/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # --- публичные методы ---

    def list_drinks(self) -> list[JsonObject]:
        return self._request_json("GET")

    def get_drink(self, drink_id: int) -> JsonObject:
        return self._request_json("GET", f"/{drink_id}")

    def create_drink(self, payload: JsonObject) -> JsonObject:
        check_payload(payload)
        return self._request_json("POST", "", payload)

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        check_payload(payload)
        return self._request_json("PUT", f"/{drink_id}", payload)

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        return self._request_json("PATCH", f"/{drink_id}", changes)

    def delete_drink(self, drink_id: int) -> None:
        # тело ответа не читаем, оно нам не нужно
        self._request("DELETE", f"/{drink_id}")

    # --- общая HTTP-логика ---

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        url = self._base_url + path
        try:
            response = requests.request(method, url, json=payload, timeout=self._timeout)
        except requests.Timeout:
            raise CoffeeTimeoutError(f"{method} {url}: сервер не ответил за {self._timeout} сек")
        except requests.RequestException as e:
            raise CoffeeApiError(f"{method} {url}: ошибка сети {e}")

        if response.status_code == 404:
            raise CoffeeNotFoundError(f"{method} {url}: не найдено")
        if response.status_code not in OK_CODES:
            raise CoffeeApiError(f"{method} {url}: код ответа {response.status_code}")
        return response

    def _request_json(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ):
        response = self._request(method, path, payload)
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise CoffeeApiError(f"{method} {path or '/'}: сервер вернул не JSON")
        try:
            return response.json()
        except ValueError:
            raise CoffeeApiError(f"{method} {path or '/'}: сервер вернул битый JSON")