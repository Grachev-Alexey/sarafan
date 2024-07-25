import os
import sys

import django
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_name.settings")
    django.setup()
    
    # Создание записей для шаблонов сообщений
    from app.models import MessageTemplate
    templates = [
        {'name': 'start_message', 'template': "👋 Привет! Добро пожаловать в сервис «Сарафан»! 🎉\n\n"},
        {'name': 'spinning_wheel_message', 'template': "🎰 Крутим колесо фортуны...\n\n"},
        {'name': 'get_discount_message', 
         'template': "🥳 Поздравляем! Вы получили скидку в {message_salon_name}! 🎉\n\nВ ближайшее время с вами свяжется администратор.\n\n📞 Контакты: {contacts}"},
        {'name': 'claim_discount', 'template': "🥳 Поздравляем! Вы получили скидку в {message_salon_name}! 🎉\n\nВ ближайшее время с вами свяжется администратор.\n\n📞 Контакты: {contacts}"}, 
        {'name': 'discount_offer', 
         'template': "✨ И вам выпадает {discount} в {message_salon_name}🤩\n\n Салон оказывает следующие услуги: {categories}! \n\nХотите забрать подарок?\n\n1 - Да / 2 - Нет (осталось {attempts_left} попытка)"},
        {'name': 'invalid_salon_id', 'template': "⛔️ Упс, неверный формат ID салона. ID должен состоять только из цифр."},
        {'name': 'salon_not_found', 'template': "😔 К сожалению, салон с таким ID не найден."},
        {'name': 'already_visited', 'template': "🤔 Вы уже получали скидку в этом салоне."},
        {'name': 'welcome_back', 'template': "😊 Рады видеть вас снова! 👋"},
        {'name': 'data_loading_error', 'template': "⚠️ Ошибка при загрузке данных. Пожалуйста, начните сначала."},
        {'name': 'spin_wheel_first', 'template': "🎰 Чтобы получить скидку, сначала нужно крутануть колесо фортуны. Напишите 'Да', чтобы начать."},
        {'name': 'user_declined', 'template': "👌 Хорошо. "},
        {'name': 'accept_terms', 'template': "😔 Извините, но для участия в акции необходимо принять условия использования сервиса. Без этого мы не можем предоставить вам скидку. Пожалуйста, ознакомьтесь с условиями и дайте согласие, чтобы продолжить."},
        {'name': 'no_discounts_available', 'template': "😔 Извините, сейчас нет доступных скидок."},
        {'name': 'general_error', 'template': "⚠️ Произошла ошибка. Пожалуйста, начните сначала."}
    ]
    for data in templates:
        if not MessageTemplate.objects.filter(name=data['name']).exists():
            MessageTemplate.objects.create(**data)

    # Создание записи для настроек весов скидок
    from app.models import DiscountWeightSettings
    if not DiscountWeightSettings.objects.exists():
        DiscountWeightSettings.objects.create(
            ratio_40_80_weight=3,
            ratio_30_40_weight=2,
            ratio_below_30_weight=1,
            partners_invited_weight=1
        )

    # Создание пользователя-администратора
    from app.models import User
    from django.contrib.auth.hashers import make_password
    sarafan_admin_user = User.objects.filter(username='sarafan_admin').first()
    if not sarafan_admin_user:
        sarafan_admin_user = User.objects.create(
            username='sarafan_admin',
            password=make_password('sarafan_admin'),
            is_superuser=True,
            is_staff=True
        )
        print('Пользователь-администратор создан!')

    execute_from_command_line(sys.argv)