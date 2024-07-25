import asyncio
import logging
import os
import requests
from typing import List, Optional, Tuple

from app import db, service
from app.models import PartnerInfo, ClientsData, ClientSalonStatus, Category, Partner
import telegram


async def get_salons_data() -> Optional[List[PartnerInfo]]:
    """Загружает данные о салонах из Google Sheets."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=os.environ.get("SHEET_ID"), range='A2:J').execute()  # Изменено количество столбцов
        values = result.get('values', [])

        if not values:
            logging.error('Не удалось найти данные в таблице.')
            return None

        salons: List[PartnerInfo] = []
        for row in values:
            if len(row) == 10:
                category, name, discount, city, contacts, salon_id, priority, linked_salon_id, message_salon_name, partner_type = row
                salon_info = PartnerInfo(
                    id=salon_id,
                    partner_type=partner_type.strip().lower(),
                    categories=[
                        db.session.query(Category).filter(Category.name == c.strip()).first()
                        for c in category.split(' • ')
                    ],
                    name=name,
                    discount=discount,
                    city=city,
                    contacts=contacts,
                    priority=(priority.strip().lower() == 'да'),
                    linked_partner_id=linked_salon_id if linked_salon_id.strip().lower() != 'нет' else None,
                    message_partner_name=message_salon_name
                )
                salons.append(salon_info)

        return salons
    except Exception as e:
        logging.error(f"Ошибка при загрузке данных из Google Sheets: {e}")
        return None


async def save_salons_data_to_db(salons: List[PartnerInfo]):
    """Сохраняет данные о салонах в базу данных."""
    for salon in salons:
        existing_salon = db.session.get(PartnerInfo, salon.id)
        if not existing_salon:
            db.session.add(salon)
        else:
            existing_salon.category = salon.category
            existing_salon.name = salon.name
            existing_salon.discount = salon.discount
            existing_salon.city = salon.city
            existing_salon.contacts = salon.contacts
            existing_salon.priority = salon.priority
            existing_salon.linked_salon_id = salon.linked_salon_id
    db.session.commit()


async def update_salons_data():
    """Обновляет данные о салонах из Google Sheets."""
    new_salons = await get_salons_data()
    if new_salons:
        await save_salons_data_to_db(new_salons)
        logging.info("Данные о салонах успешно обновлены.")
    else:
        logging.error("Не удалось обновить данные о салонах.")


async def send_message(chat_id: str, message: str) -> Optional[dict]:
    """Отправляет сообщение пользователю через WhatsApp API."""
    logging.info(f"Отправка сообщения на номер {chat_id}: {message}")
    data = {
        'to': chat_id,
        'body': message
    }
    headers = {
        'Authorization': f'Bearer {os.environ.get("WHAPI_API_KEY")}',
        'Content-Type': 'application/json'
    }
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.post(os.environ.get("WHAPI_BASE_URL"), json=data, headers=headers)
        )
        response.raise_for_status()
        logging.info(f"Ответ от WHAPI: {response.status_code} {response.text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        return None


async def create_amocrm_contact(client_data: ClientsData) -> Optional[int]:
    """Создает контакт в AmoCRM и возвращает его ID.
    Если контакт с таким номером уже существует, возвращается его ID.
    """
    existing_contact_id = await get_amocrm_contact_id(client_data.chat_id)
    if existing_contact_id:
        logging.info(f"Контакт с номером {client_data.chat_id} уже существует в AmoCRM, ID: {existing_contact_id}")
        return existing_contact_id

    url = f'https://{os.environ.get("AMOCRM_SUBDOMAIN")}.amocrm.ru/api/v4/contacts'
    headers = {
        'Authorization': f'Bearer {os.environ.get("AMOCRM_API_KEY")}',
        'Content-Type': 'application/json'
    }
    contact_data = {
        'name': client_data.client_name,
        'custom_fields_values': [
            {'field_id': 265455, 'values': [{'value': client_data.chat_id}]}
        ]
    }
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.post(url, headers=headers, json=[contact_data])
        )
        response.raise_for_status()
        response_data = response.json()
        contact_id = response_data['_embedded']['contacts'][0]['id']
        logging.info(f"Контакт успешно создан в AmoCRM, ID: {contact_id}")
        return contact_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при создании контакта в AmoCRM: {e}")
        return None


async def create_or_update_amocrm_lead(client_data: ClientsData, contact_id: int):
    """Создает или обновляет сделку в AmoCRM, привязанную к контакту."""
    url = f'https://{os.environ.get("AMOCRM_SUBDOMAIN")}.amocrm.ru/api/v4/leads'
    headers = {
        'Authorization': f'Bearer {os.environ.get("AMOCRM_API_KEY")}',
        'Content-Type': 'application/json'
    }

    # Получаем список сделок, привязанных к контакту
    contact_leads_url = f'https://{os.environ.get("AMOCRM_SUBDOMAIN")}.amocrm.ru/api/v4/contacts/{contact_id}/links'
    contact_leads_payload = {"to": "leads"}
    contact_leads_response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: requests.get(contact_leads_url, headers=headers, json=contact_leads_payload)
    )

    if contact_leads_response.status_code == 200:
        contact_leads_data = contact_leads_response.json()
        lead_id = None
        for lead in contact_leads_data["_embedded"]["links"]:
            # Ищем сделку, относящуюся к текущему салону (по полю ID Салона)
            lead_url = f'https://{os.environ.get("AMOCRM_SUBDOMAIN")}.amocrm.ru/api/v4/leads/{lead["to_entity_id"]}'
            lead_response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.get(lead_url, headers=headers)
            )
            if lead_response.status_code == 200:
                lead_data = lead_response.json()
                for field in lead_data.get("custom_fields_values", []):
                    if field["field_id"] == 267157 and field["values"][0]["value"] == client_data.initial_salon_id:
                        lead_id = lead["to_entity_id"]
                        break
            if lead_id:  # Если нашли сделку, выходим из цикла
                break

        if lead_id:
            # Обновляем существующую сделку
            update_url = f'{url}/{lead_id}'
            lead_data = {
                'custom_fields_values': [
                    {'field_id': 267159, 'values': [{'value': client_data.claimed_salon_name}]},
                    {'field_id': 267161, 'values': [{'value': client_data.claimed_salon_id}]}
                ]
            }
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.patch(update_url, headers=headers, json=lead_data)
            )
            if response.status_code == 200 or response.status_code == 204:
                logging.info(f"Сделка успешно обновлена в AmoCRM, ID: {lead_id}")
            else:
                logging.error(f"Ошибка при обновлении сделки в AmoCRM: {response.status_code} {response.text}")
        else:
            # Создаем новую сделку, привязанную к контакту
            lead_data = {
                'name': 'Сделка из WhatsApp',
                '_embedded': {
                    'contacts': [{'id': contact_id}]
                },
                'custom_fields_values': [
                    {'field_id': 267155, 'values': [{'value': client_data.initial_salon_name}]},
                    {'field_id': 267157, 'values': [{'value': client_data.initial_salon_id}]},
                    {'field_id': 267159, 'values': [{'value': client_data.claimed_salon_name}]},
                    {'field_id': 267161, 'values': [{'value': client_data.claimed_salon_id}]},
                    {'field_id': 267163, 'values': [{'value': client_data.city}]}
                ]
            }
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.post(url, headers=headers, json=[lead_data])
            )
            if response.status_code == 200 or response.status_code == 204:
                logging.info(f"Сделка успешно создана и привязана к контакту в AmoCRM")
            else:
                logging.error(f"Ошибка при создании сделки в AmoCRM: {response.status_code} {response.text}")
    else:
        logging.error(f"Ошибка при получении списка сделок контакта: {contact_leads_response.status_code} {contact_leads_response.text}")



async def get_amocrm_contact_id(phone_number: str) -> Optional[int]:
    """Получает ID контакта из AmoCRM по номеру телефона."""
    url = f'https://{os.environ.get("AMOCRM_SUBDOMAIN")}.amocrm.ru/api/v4/contacts?query={phone_number}'
    headers = {
        'Authorization': f'Bearer {os.environ.get("AMOCRM_API_KEY")}'
    }
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(url, headers=headers)
        )
        response.raise_for_status()
        data = response.json()
        if data['_embedded']['contacts']:
            return data['_embedded']['contacts'][0]['id']
        else:
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении ID контакта из AmoCRM: {e}")
        return None
        
async def set_salon_status(client_id: int, salon_id: str, status: str):
    """Устанавливает статус салона для клиента."""
    existing_status = ClientSalonStatus.query.filter_by(client_id=client_id, salon_id=salon_id).first()
    if existing_status:
        existing_status.status = status
    else:
        new_status = ClientSalonStatus(client_id=client_id, salon_id=salon_id, status=status)
        db.session.add(new_status)
    db.session.commit()

async def get_salon_status(client_id: int, salon_id: str) -> Optional[str]:
    """Возвращает статус салона для клиента."""
    status = ClientSalonStatus.query.filter_by(client_id=client_id, salon_id=salon_id).first()
    return status.status if status else None     

async def send_telegram_notification(chat_id: int, message: str) -> Optional[bool]:
    """Отправляет сообщение в Telegram."""
    logging.info(f"Отправка сообщения в Telegram на ID чата {chat_id}: {message}")
    bot = telegram.Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logging.info("Сообщение успешно отправлено в Telegram.")
        return True
    except telegram.error.TelegramError as e:
        logging.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        return False