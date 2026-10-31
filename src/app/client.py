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
"""

import requests

from app.exceptions import CoffeeApiError, CoffeeNotFoundError, CoffeeTimeoutError

JsonObject = dict[str, object]

FIELDS = ("title", "description", "ingredients", "image")
OK_CODES = (200, 201)


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://api.sampleapis.com/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        return self._request("GET").json()

    def get_drink(self, drink_id: int) -> JsonObject:
        return self._request("GET", f"/{drink_id}").json()

    def create_drink(self, payload: JsonObject) -> JsonObject:
        self._check_payload(payload)
        return self._request("POST", "", payload).json()

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        self._check_payload(payload)
        return self._request("PUT", f"/{drink_id}", payload).json()

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        return self._request("PATCH", f"/{drink_id}", changes).json()

    def delete_drink(self, drink_id: int) -> None:
        self._request("DELETE", f"/{drink_id}")

    def _check_payload(self, payload: JsonObject) -> None:
        for field in FIELDS:
            if field not in payload:
                raise ValueError(f"в напитке нет поля {field}")

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

        if method == "DELETE":
            return response

        if "application/json" not in response.headers.get("Content-Type", ""):
            raise CoffeeApiError(f"{method} {url}: сервер вернул не JSON")
        try:
            response.json()
        except ValueError:
            raise CoffeeApiError(f"{method} {url}: сервер вернул битый JSON")
        return response