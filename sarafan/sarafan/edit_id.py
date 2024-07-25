from app import db, create_app
from sqlalchemy import text

app = create_app()

# Словарь с новыми ID: {старый_ID: новый_ID}
new_salon_ids = {
    "t103322": "т212121",
    # ...
}

with app.app_context():
    for old_id, new_id in new_salon_ids.items():
        try:
            with db.engine.connect() as connection:
                # 1. Копируем данные из старой записи в новую с новым ID
                connection.execute(
                    text(f"""
                        INSERT INTO salon_info (id, category, name, discount, city, contacts, clients_brought, clients_received, priority, linked_salon_id)
                        SELECT '{new_id}', category, name, discount, city, contacts, clients_brought, clients_received, priority, linked_salon_id
                        FROM salon_info
                        WHERE id = '{old_id}'
                    """)
                )

                # 2. Обновляем ссылки на салон в partners и client_salon_status
                connection.execute(
                    text(f"UPDATE partners SET salon_id = '{new_id}' WHERE salon_id = '{old_id}'")
                )
                connection.execute(
                    text(f"UPDATE client_salon_status SET salon_id = '{new_id}' WHERE salon_id = '{old_id}'")
                )

                # 3. Удаляем старую запись из salon_info
                connection.execute(
                    text(f"DELETE FROM salon_info WHERE id = '{old_id}'")
                )

                # Фиксируем изменения в базе данных
                connection.commit()

            print(f"ID салона {old_id} успешно изменен на {new_id}")
        except Exception as e:
            print(f"Ошибка при изменении ID салона {old_id}: {e}")