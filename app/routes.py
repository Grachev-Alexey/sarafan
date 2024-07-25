import asyncio
import logging
import time

from flask import request, jsonify, Blueprint
from app import db
from app.models import ClientsData, PartnerInfo, ClientSalonStatus, MessageTemplate, Category, City, Partner
from app.services import (
    update_salons_data,
    send_message,
    create_amocrm_contact,
    create_or_update_amocrm_lead,
    get_amocrm_contact_id,
    set_salon_status,
    get_salon_status,
    send_telegram_notification
)
from app.utils import get_random_discount
import os

bp = Blueprint('routes', __name__)


@bp.route('/webhook', methods=['POST'])
async def webhook():
    """Обрабатывает входящие webhook-запросы от WhatsApp."""
    data = request.json
    logging.info(f"Received data: {data}")

    event_type = data.get('event', {}).get('type')

    if event_type == 'messages':
        message_data = data.get('messages', [])[0]
        chat_id = message_data.get('chat_id', '').replace('@s.whatsapp.net', '')
        message_body = message_data.get('text', {}).get('body', '').lower()

        if not chat_id or not message_body:
            logging.error("Missing phone number or message in received data")
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        try:
            await handle_incoming_message(chat_id, message_body, message_data)
        except Exception as e:
            logging.error(f"Error handling incoming message: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "ok"}), 200


async def handle_incoming_message(chat_id: str, message_body: str, message_data: dict):
    """Обрабатывает входящее сообщение от пользователя."""
    start_time = time.time()
    logging.info(f"Обработка сообщения для номера телефона: {chat_id}, сообщение: {message_body}")

    if message_data.get('from_me', False):
        logging.info("Пропускаем обработку сообщения, отправленного ботом")
        return

    if chat_id == os.environ.get("BOT_CHAT_ID"):
        logging.info("Пропускаем отправку сообщения самому себе")
        return

    message_body_lower = message_body.lower()

    if message_body_lower.startswith("получить подарок"):
        await handle_start_command(chat_id, message_body_lower, message_data)
    elif message_body_lower in ['да', '1', '2', 'нет'] or message_body.isdigit():
        await handle_user_response(chat_id, message_body_lower)
    elif message_body_lower == 'update data':
        await update_salons_data()
        await send_message(chat_id, "Данные успешно обновлены")
    else:
        logging.info("Сообщение не относится к логике бота и будет проигнорировано")


async def handle_start_command(chat_id: str, message_body: str, message_data: dict):
    """Обрабатывает команду 'Начать' от пользователя."""
    partner_id = message_body.split("получить подарок (", 1)[-1].replace(")", "").strip()
    client_name = message_data.get('from_name', 'Клиент')

    partner = PartnerInfo.query.get(partner_id)
    if not partner:
        await send_message(chat_id, await get_template_or_default('salon_not_found'))
        return

    client_data = ClientsData.query.filter_by(chat_id=chat_id).first()

    # Проверка статуса салона для клиента
    existing_salon_status = None
    if client_data:
        existing_salon_status = await get_salon_status(client_data.id, partner_id)
        if existing_salon_status == 'visited':
            await send_message(chat_id, await get_template_or_default('already_visited'))
            return

    # Новый пользователь или пользователь не взаимодействовал с этим салоном
    if not client_data:
        # Получаем объект City по названию
        city = City.query.filter_by(name=partner.city.name).first()

        client_data = ClientsData(
            chat_id=chat_id,
            initial_salon_name=partner.name,
            initial_salon_id=partner_id,
            client_name=client_name,
            city=partner.city.name,
            discount_claimed=False,
            claimed_salon_name=None,
            claimed_salon_id=None,
            attempts_left=1,
        )
        db.session.add(client_data)
        db.session.flush()
        await set_salon_status(client_data.id, partner_id, 'visited') 

        # Отправка приветственного сообщения из шаблона
        start_message = await get_template_or_default('start_message')
        await send_message(chat_id, start_message)
    else:
        # Обновляем данные пользователя
        client_data.initial_salon_name = partner.name
        client_data.initial_salon_id = partner_id
        # Получаем объект City по названию
        city = City.query.filter_by(name=partner.city.name).first()

        client_data.city = partner.city.name
        client_data.discount_claimed = False
        client_data.claimed_salon_name = None
        client_data.claimed_salon_id = None
        client_data.attempts_left = 1
        # Старый пользователь
        await send_message(chat_id, await get_template_or_default('welcome_back'))

    #  Если статус уже был установлен (claimed или rejected), не меняем его
    if existing_salon_status not in ('claimed', 'rejected'):
        await set_salon_status(client_data.id, partner_id, 'visited')

    partner.clients_brought += 1
    db.session.commit()
    logging.info(f"Данные сохранены в базе данных: {client_data}")

    # Создаем контакт в AmoCRM
    contact_id = await create_amocrm_contact(client_data)
    if contact_id:
        # Создаем сделку в AmoCRM
        await create_or_update_amocrm_lead(client_data, contact_id)

    await handle_discount_request(chat_id, client_data)


async def handle_user_response(chat_id: str, message_body: str):
    """Обрабатывает ответ пользователя на запрос о скидке."""
    client_data = ClientsData.query.filter_by(chat_id=chat_id).first()
    if not client_data:
        await send_message(chat_id, await get_template_or_default('data_loading_error'))
        return

    if message_body == "да" and not client_data.discount_claimed:
        await handle_discount_request(chat_id, client_data)
    elif message_body in ['1', '2']:
        # Обрабатываем ответы "1" и "2" только если салон не приоритетный
        if client_data.chosen_salon_id:
            if message_body == '1':
                await handle_claim_discount(chat_id, client_data)
            else:
                await set_salon_status(client_data.id, client_data.chosen_salon_id, 'rejected')
                client_data.attempts_left -= 1
                db.session.commit()

                if client_data.attempts_left > 0:
                    await handle_discount_request(chat_id, client_data)
                else:
                    await send_spinning_wheel_message(chat_id)
                    await handle_no_attempts_left(chat_id, client_data)
        else:
            await send_message(chat_id, await get_template_or_default('spin_wheel_first'))
    elif message_body == 'нет':
        await send_message(chat_id, await get_template_or_default('user_declined'))
    else:
        await send_message(chat_id, await get_template_or_default('accept_terms'))


async def handle_discount_request(chat_id: str, client_data: ClientsData):
    """Обрабатывает запрос на скидку и отправляет сообщение с результатом."""
    if client_data.attempts_left > 0:
        await send_spinning_wheel_message(chat_id)
        discount_message = await get_discount_message(client_data)
        await send_message(chat_id, discount_message)
    else:
        await handle_no_attempts_left(chat_id, client_data)


async def handle_no_attempts_left(chat_id: str, client_data: ClientsData):
    """Обрабатывает ситуацию, когда у пользователя не осталось попыток."""
    # Выбираем случайный салон
    discount_data = await get_random_discount(client_data)
    if not discount_data:
        await send_message(chat_id, await get_template_or_default('no_discounts_available'))
        return

    chosen_salon, _ = discount_data

    # Сохраняем выбранный салон и устанавливаем статус 'claimed'
    client_data.chosen_salon_id = chosen_salon.id
    client_data.chosen_salon_name = chosen_salon.name
    await set_salon_status(client_data.id, chosen_salon.id, 'claimed')
    client_data.discount_claimed = True
    chosen_salon.clients_received += 1
    db.session.commit()

    # Отправка сообщения о результате из шаблона
    get_discount_message = await get_template_or_default(
        'get_discount_message',
        discount=chosen_salon.discount,
        salon_name=chosen_salon.name,
        contacts=chosen_salon.contacts,
        categories=", ".join([category.name for category in chosen_salon.categories])
    )
    await send_message(chat_id, get_discount_message)

    # Обновляем сделку в AmoCRM
    contact_id = await get_amocrm_contact_id(client_data.chat_id)
    if contact_id:
        await create_or_update_amocrm_lead(client_data, contact_id)


async def handle_claim_discount(chat_id: str, client_data: ClientsData):
    """Обрабатывает запрос пользователя на получение скидки."""
    if client_data and client_data.chosen_salon_id:
        chosen_salon = PartnerInfo.query.get(client_data.chosen_salon_id)
        if chosen_salon:
            #  Изменение client_salon_status
            await set_salon_status(client_data.id, chosen_salon.id, 'claimed')

            client_data.discount_claimed = True
            client_data.claimed_salon_name = chosen_salon.name
            client_data.claimed_salon_id = chosen_salon.id
            chosen_salon.clients_received += 1
            db.session.commit()

            # Отправка сообщения с поздравлением из шаблона
            claim_discount_message = await get_template_or_default(
                'claim_discount',
                salon_name=chosen_salon.name,
                contacts=chosen_salon.contacts,
                message_salon_name=chosen_salon.message_partner_name
            )
            await send_message(chat_id, claim_discount_message)

            # Обновляем сделку в AmoCRM
            contact_id = await get_amocrm_contact_id(client_data.chat_id)
            if contact_id:
                await create_or_update_amocrm_lead(client_data, contact_id)

            # Отправка оповещения партнеру о полученном клиенте
            partner_chat_id = chosen_salon.owner.telegram_chat_id
            if partner_chat_id:
                message = f"🎉 Новый клиент! 🎉\n\n{client_data.client_name} ({client_data.chat_id}) воспользовался(ась) вашей скидкой."
                await send_telegram_notification(partner_chat_id, message)

            # Отправка оповещения партнеру, который привел клиента, о привлеченном клиенте
            initial_salon = PartnerInfo.query.get(client_data.initial_salon_id)
            if initial_salon and initial_salon.owner and initial_salon.owner.telegram_chat_id:
                inviting_partner_chat_id = initial_salon.owner.telegram_chat_id
                message = f"🎉 Вы привели нового клиента! 🎉\n\n{client_data.client_name} ({client_data.chat_id}) воспользовался(ась) скидкой в салоне {chosen_salon.name}."
                await send_telegram_notification(inviting_partner_chat_id, message)

        else:
            logging.warning("Не найдены контактные данные салона для этого пользователя")
            await send_message(chat_id, await get_template_or_default('general_error'))
    else:
        logging.warning("Не найдены данные о салоне для этого пользователя")
        await send_message(chat_id, await get_template_or_default('general_error'))


async def send_spinning_wheel_message(chat_id: str):
    """Отправляет сообщение "Запускаю колесо фортуны...".
    """
    # Отправка сообщения о запуске колеса фортуны из шаблона
    spinning_wheel_message = await get_template_or_default('spinning_wheel_message')
    await send_message(chat_id, spinning_wheel_message)
    await asyncio.sleep(3)


async def get_discount_message(client_data: ClientsData) -> str:
    """Возвращает сообщение с информацией о скидке или ошибке."""
    discount_data = await get_random_discount(client_data)
    if not discount_data:
        return await get_template_or_default('no_discounts_available')

    chosen_salon, is_priority = discount_data
    client_data.chosen_salon_id = chosen_salon.id
    client_data.chosen_salon_name = chosen_salon.name
    db.session.commit()

    # Формируем строку с категориями
    categories_str = ", ".join([category.name for category in chosen_salon.categories])

    if is_priority:
        #  Если салон приоритетный, сразу записываем данные в claimed_*
        await handle_claim_discount(client_data.chat_id, client_data)
        return await get_template_or_default(
            'get_discount_message',
            discount=chosen_salon.discount,
            salon_name=chosen_salon.name,
            contacts=chosen_salon.contacts,
            message_salon_name=chosen_salon.message_partner_name,
            categories=categories_str  # Передаем категории в шаблон
        )
    else:
        # Отправка предложения скидки из шаблона
        discount_offer_message = await get_template_or_default(
            'discount_offer',
            discount=chosen_salon.discount,
            salon_name=chosen_salon.name,
            attempts_left=client_data.attempts_left,
            message_salon_name=chosen_salon.message_partner_name,
            categories=categories_str  # Передаем категории в шаблон
        )
        return discount_offer_message


async def get_template_or_default(template_name: str, **kwargs) -> str:
    """Возвращает шаблон сообщения из базы данных или сообщение по умолчанию,
       если шаблон не найден.
    """
    template = MessageTemplate.query.filter_by(name=template_name).first()
    if template:

        return template.template.format(**kwargs) 
    else:
        # Вернуть сообщение по умолчанию для данного шаблона
        return {
            'invalid_salon_id': "Неверный формат ID салона. ID должен состоять только из цифр.",
            'salon_not_found': "Салон с таким ID не найден.",
            'already_visited': "Вы уже получали скидку в этом салоне.",
            'welcome_back': "Рады видеть Вас снова!",
            'data_loading_error': "Ошибка при загрузке данных. Пожалуйста, начните сначала.",
            'spin_wheel_first': "Чтобы получить скидку, сначала нужно сыграть в колесо фортуны. Напишите 'Да', чтобы начать.",
            'user_declined': "Хорошо. ",
            'accept_terms': "Извините, но для участия в акции необходимо принять условия использования сервиса. Без этого мы не можем предоставить вам скидку. Пожалуйста, ознакомьтесь с условиями и дайте согласие, чтобы продолжить.",
            'no_discounts_available': "Извините, нет доступных скидок.",
            'spinning_wheel_message': " Запускаю колесо фортуны...",
            'get_discount_message': "✨ И вам выпадает {discount} в {message_salon_name} ({categories})! 🤩\n\n📞 Контакты: {contacts}",
            'claim_discount': "Поздравляем! В ближайшее время с Вами свяжется администратор из {message_salon_name}.\n\n Контактные данные: {contacts}",
            'discount_offer': "✨ И вам выпадает {discount} в {message_salon_name} ({categories})! 🤩\n\nХотите забрать подарок?\n\n1 - Да / 2 - Нет (осталось {attempts_left} попытка)",
            'general_error': "Произошла ошибка. Пожалуйста, попробуйте позже."
        }.get(template_name, "Произошла ошибка. Попробуйте позже.")