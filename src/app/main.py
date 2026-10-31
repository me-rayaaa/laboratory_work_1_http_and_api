import sys
from uuid import uuid4

from app.client import SampleApisCoffeeClient
from app.exceptions import CoffeeApiError, CoffeeNotFoundError, CoffeeTimeoutError


def check_fields(actual: dict, expected: dict, stage: str) -> None:
    """Сравнивает поля ответа с тем, что отправили. Если что-то не совпало - ValueError."""
    for field, value in expected.items():
        if actual.get(field) != value:
            raise ValueError(
                f"{stage}: поле {field} = {actual.get(field)!r}, ожидали {value!r}"
            )


def main() -> int:
    # можно передать другой адрес, например мок:
    # PYTHONPATH=src python -m app.main http://127.0.0.1:8000/coffee/hot
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://api.sampleapis.com/coffee/hot"
    client = SampleApisCoffeeClient(base_url=base_url)
    marker = uuid4().hex[:8]
    created_id = None
    print(f"Метка группы: {marker}")
    try:
        # 1. GET коллекции
        drinks = client.list_drinks()
        print(f"[1/7] GET коллекции: всего напитков - {len(drinks)}")

        # 2. POST: создаём свой напиток, метка в названии
        new_drink = {
            "title": f"Raf {marker}",
            "description": "Espresso with cream and vanilla sugar",
            "ingredients": ["Espresso", "Cream", "Vanilla sugar"],
            "image": "https://example.com/raf.jpg",
        }
        try:
            created = client.create_drink(new_drink)
        except CoffeeTimeoutError:
            # POST мог дойти до сервера, просто ответ не успел вернуться.
            # Повторять нельзя - получится дубликат.
            print(
                "[2/7] POST: тайм-аут, неизвестно, создалась ли запись. "
                f"Повторять не будем. Проверьте вручную по метке {marker}: "
                f"GET {base_url.rstrip('/')}?title_like={marker}"
            )
            return 1
        created_id = created["id"]
        print(f"[2/7] POST: создан напиток id={created_id}, title={created['title']!r}")

        # 3. GET по id: сохранилось то, что отправили
        fetched = client.get_drink(created_id)
        check_fields(fetched, new_drink, "GET после POST")
        print(f"[3/7] GET id={created_id}: все поля совпадают с отправленными")

        # 4. PUT: полная замена + повторный GET
        replacement = {
            "title": f"Raf {marker} (PUT)",
            "description": "Fully replaced: raf with lavender",
            "ingredients": ["Espresso", "Cream", "Lavender syrup"],
            "image": "https://example.com/raf-lavender.jpg",
        }
        client.replace_drink(created_id, replacement)
        after_put = client.get_drink(created_id)
        check_fields(after_put, replacement, "GET после PUT")
        print(f"[4/7] PUT + GET: все {len(replacement)} поля заменились")

        # 5. PATCH: меняем только описание + повторный GET
        changes = {"description": "Patched: less sugar"}
        client.update_drink(created_id, changes)
        after_patch = client.get_drink(created_id)
        check_fields(after_patch, changes, "GET после PATCH")
        unchanged = {k: v for k, v in replacement.items() if k not in changes}
        check_fields(after_patch, unchanged, "GET после PATCH (остальные поля)")
        print("[5/7] PATCH + GET: description обновился, остальные поля на месте")

        # 6. DELETE
        client.delete_drink(created_id)
        print(f"[6/7] DELETE id={created_id}: ок")

        # 7. GET после удаления - ждём 404
        try:
            client.get_drink(created_id)
        except CoffeeNotFoundError:
            print(f"[7/7] GET id={created_id}: 404, запись удалена")
            created_id = None
        else:
            raise ValueError(f"после DELETE запись id={created_id} всё ещё есть")

        print("Сценарий выполнен")
    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка: {error}. Метка группы: {marker}")
        return 1
    finally:
        if created_id is not None:
            try:
                client.delete_drink(created_id)
                print(f"Уборка: удалили id={created_id}")
            except CoffeeNotFoundError:
                pass
            except CoffeeApiError as error:
                print(f"Не удалось удалить id={created_id}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
