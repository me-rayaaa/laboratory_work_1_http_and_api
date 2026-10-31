from uuid import uuid4

from app.client import SampleApisCoffeeClient
from app.exceptions import CoffeeApiError, CoffeeNotFoundError, CoffeeTimeoutError


def same_fields(drink, expected):
    for key in expected:
        if drink[key] != expected[key]:
            return False
    return True


def show_list(client):
    drinks = client.list_drinks()
    print("1. Получили список, всего напитков:", len(drinks))


def create(client, marker):
    new_drink = {
        "title": f"Raf {marker}",
        "description": "Espresso with cream and vanilla sugar",
        "ingredients": ["Espresso", "Cream", "Vanilla sugar"],
        "image": "https://example.com/raf.jpg",
    }
    try:
        created = client.create_drink(new_drink)
    except CoffeeTimeoutError:
        # повторять POST нельзя, запись могла уже создаться
        print("2. POST не дождался ответа, неизвестно создалась ли запись. Повторять не будем")
        raise
    print("2. Создали напиток, id =", created["id"])
    return created["id"], new_drink


def check_created(client, drink_id, sent):
    drink = client.get_drink(drink_id)
    if not same_fields(drink, sent):
        raise ValueError("после POST данные не совпали")
    print("3. GET после POST: данные совпадают")


def replace(client, drink_id, marker):
    new_data = {
        "title": f"Raf {marker} v2",
        "description": "Raf with lavender",
        "ingredients": ["Espresso", "Cream", "Lavender syrup"],
        "image": "https://example.com/raf2.jpg",
    }
    client.replace_drink(drink_id, new_data)
    drink = client.get_drink(drink_id)
    if not same_fields(drink, new_data):
        raise ValueError("после PUT данные не заменились")
    print("4. PUT: все поля заменились")
    return new_data


def patch(client, drink_id, old_data):
    changes = {"description": "Less sugar"}
    client.update_drink(drink_id, changes)
    drink = client.get_drink(drink_id)
    if not same_fields(drink, changes):
        raise ValueError("после PATCH описание не поменялось")
    rest = {key: old_data[key] for key in old_data if key not in changes}
    if not same_fields(drink, rest):
        raise ValueError("после PATCH поменялись другие поля")
    print("5. PATCH: описание поменялось, остальное осталось")


def delete(client, drink_id):
    client.delete_drink(drink_id)
    print("6. DELETE: удалили")
    try:
        client.get_drink(drink_id)
    except CoffeeNotFoundError:
        print("7. GET после удаления: 404, все ок")
        return
    raise ValueError("напиток не удалился")


def cleanup(client, drink_id):
    # сюда попадаем, только если сценарий упал после создания записи
    try:
        client.delete_drink(drink_id)
        print("Удалили за собой напиток id =", drink_id)
    except CoffeeNotFoundError:
        pass
    except CoffeeApiError as error:
        print(f"Не удалось удалить id={drink_id}: {error}")


def main() -> int:
    client = SampleApisCoffeeClient()
    # если API не работает, запускаем мок и берем его адрес:
    # client = SampleApisCoffeeClient(base_url="http://127.0.0.1:8000/coffee/hot")
    marker = uuid4().hex[:8]
    created_id = None
    try:
        show_list(client)
        created_id, sent = create(client, marker)
        check_created(client, created_id, sent)
        new_data = replace(client, created_id, marker)
        patch(client, created_id, new_data)
        delete(client, created_id)
        created_id = None
    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка: {error}. Метка группы: {marker}")
        return 1
    finally:
        if created_id is not None:
            cleanup(client, created_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())