import os
from app import db, create_app
from app.models import City

app = create_app()
app.app_context().push()

def fill_cities():
    with open('cities.txt', 'r', encoding='utf-8') as f:
        # Пропускаем заголовок
        next(f)

        for line in f:
            city_name = line.strip().split(',')[0]  # Извлекаем название города
            existing_city = City.query.filter_by(name=city_name).first()
            if not existing_city:
                city = City(name=city_name)
                db.session.add(city)

    db.session.commit()
    print(f"Города успешно добавлены в базу данных.")

if __name__ == '__main__':
    fill_cities()