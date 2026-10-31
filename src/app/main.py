from uuid import uuid4

from app.business_logic import (
    check_created,
    cleanup,
    create,
    delete,
    patch,
    replace,
    show_list,
)
from app.client import SampleApisCoffeeClient
from app.exceptions import CoffeeApiError


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