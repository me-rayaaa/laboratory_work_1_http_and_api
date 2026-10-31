"""
Описание запроса создания горячего кофе
---------------------------------------

Запрос:
    POST https://api.sampleapis.com/coffee/hot
    (для мока: POST http://127.0.0.1:8000/coffee/hot)

Заголовки:
    Content-Type: application/json  - обязателен. Без него сервер не разбирает
                                      тело как JSON и отвечает 400.
                                      requests ставит его сам, если передать json=...
    Accept: application/json        - не обязателен, сервер и так отвечает JSON.

Тело (JSON-объект):
    | поле        | тип        | обязательное | что это                    |
    |-------------|------------|--------------|----------------------------|
    | title       | str        | да           | название напитка           |
    | description | str        | да           | описание                   |
    | ingredients | list[str]  | да           | список ингредиентов        |
    | image       | str (URL)  | да           | ссылка на картинку         |
    | id          | int        | нет          | НЕ передаём, его даёт сервер |

    Пример:
        {
            "title": "Raf ab12cd34",
            "description": "Espresso with cream and vanilla sugar",
            "ingredients": ["Espresso", "Cream", "Vanilla sugar"],
            "image": "https://example.com/raf.jpg"
        }

Кто что задаёт:
    - клиент: title, description, ingredients, image;
    - сервер: id (максимальный целый id + 1).

Успешный ответ:
    201 Created, Content-Type: application/json,
    тело - созданный объект целиком вместе с id:
        {"title": "...", "description": "...", "ingredients": [...], "image": "...", "id": 21}
    плюс заголовок Location: /coffee/hot/21

Ошибки:
    400 + {"message": "The data you are sending does not match the existing data object.",
           "expected": {...}, "received": {...}} - если не хватает какого-то поля;
    400 + "Something went wrong handling that request." - если JSON битый.

Что подтверждено запросами к API (и к mock_server, который повторяет API):
    - нужны все 4 поля, иначе 400;
    - типы и значения сервер НЕ проверяет: title: 5 или пустая строка проходят,
      лишние поля тоже сохраняются;
    - POST отвечает 201, а не 200;
    - id выдаёт сервер, после удаления последней записи её id выдаётся снова;
    - PUT берёт id из URL, id в теле игнорирует;
    - PATCH принимает только известные поля, {} или неизвестное поле -> 400;
    - DELETE отвечает 200 и {} (а не 204), повторный DELETE -> 404 и {};
    - нет записи -> 404 и {}.

Что проверяю только в клиенте (сервер этого не делает):
    - title, description, image - непустые строки;
    - ingredients - непустой список строк;
    - id в теле POST не передаём (в PUT можно, сервер его всё равно игнорирует);
    - в PATCH только известные поля и хотя бы одно.
"""

import requests

from app.exceptions import CoffeeApiError, CoffeeNotFoundError, CoffeeTimeoutError

JsonObject = dict[str, object]

# поля напитка, которые задаёт клиент (id задаёт сервер)
DRINK_FIELDS = ("title", "description", "ingredients", "image")

# какие статусы считаем успешными (POST отвечает 201, остальные 200)
OK_STATUSES = (200, 201)


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://api.sampleapis.com/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        data = self._read_json(self._request("GET"))
        if not isinstance(data, list):
            raise CoffeeApiError("GET коллекции: ожидался список напитков")
        return data

    def get_drink(self, drink_id: int) -> JsonObject:
        return self._read_object(self._request("GET", f"/{drink_id}"))

    def create_drink(self, payload: JsonObject) -> JsonObject:
        if "id" in payload:
            raise ValueError("id в POST не передаём, его назначает сервер")
        check_full_payload(payload)
        return self._read_object(self._request("POST", payload=payload))

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        check_full_payload(payload)
        return self._read_object(self._request("PUT", f"/{drink_id}", payload))

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        check_changes(changes)
        return self._read_object(self._request("PATCH", f"/{drink_id}", changes))

    def delete_drink(self, drink_id: int) -> None:
        # тело ответа не нужно: API отдаёт {}, но может прийти и пустое
        self._request("DELETE", f"/{drink_id}")

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        url = self._base_url + path
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except requests.Timeout as error:
            raise CoffeeTimeoutError(
                f"{method} {url}: нет ответа за {self._timeout} с"
            ) from error
        except requests.RequestException as error:
            raise CoffeeApiError(f"{method} {url}: сетевая ошибка ({error})") from error

        # статус проверяем до того, как трогать тело
        if response.status_code == 404:
            raise CoffeeNotFoundError(f"{method} {url}: запись не найдена (404)")
        if response.status_code not in OK_STATUSES:
            raise CoffeeApiError(
                f"{method} {url}: статус {response.status_code}{server_message(response)}"
            )
        return response

    def _read_object(self, response: requests.Response) -> JsonObject:
        data = self._read_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("ожидался JSON-объект напитка")
        return data

    @staticmethod
    def _read_json(response: requests.Response) -> object:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise CoffeeApiError(
                f"ожидался JSON, а пришёл {content_type or 'ответ без Content-Type'}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise CoffeeApiError("сервер прислал некорректный JSON") from error


def server_message(response: requests.Response) -> str:
    """Достаёт message из JSON-ошибки сервера, если он есть."""
    if "application/json" not in response.headers.get("Content-Type", ""):
        return ""
    try:
        body = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict) and body.get("message"):
        return f" ({body['message']})"
    return ""


def check_full_payload(payload: JsonObject) -> None:
    """Проверка тела для POST и PUT. Сервер типы не проверяет, поэтому проверяем сами."""
    missing = [field for field in DRINK_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"не хватает полей: {', '.join(missing)}")
    for field in ("title", "description", "image"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} должен быть непустой строкой")
    check_ingredients(payload["ingredients"])


def check_changes(changes: JsonObject) -> None:
    """Проверка тела для PATCH: хотя бы одно поле и только известные."""
    if not changes:
        raise ValueError("PATCH без изменений не отправляем")
    unknown = [field for field in changes if field not in DRINK_FIELDS]
    if unknown:
        raise ValueError(f"неизвестные поля: {', '.join(unknown)}")
    if "ingredients" in changes:
        check_ingredients(changes["ingredients"])


def check_ingredients(value: object) -> None:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError("ingredients должен быть непустым списком строк")