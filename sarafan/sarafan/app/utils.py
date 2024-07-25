import asyncio
import logging
import random
from typing import Optional, Tuple

from .models import Partner, PartnerInfo, ClientsData, DiscountWeightSettings, Category

logger = logging.getLogger(__name__)

async def get_random_discount(client_data: ClientsData) -> Optional[Tuple[PartnerInfo, bool]]:
    """
    Возвращает случайную скидку, исключая:
     - категорию салона пользователя,
     - посещенные салоны,
     - салоны, от которых пользователь отказался.
    Учитывает приоритет салонов, соотношение "привел/получил" и количество приглашенных партнеров салоном.
    В первую очередь проверяет наличие приоритетного салона для этого города,
    затем наличие связанного салона.
    """
    logger.info(f"Получение случайной скидки с учетом связанного салона, приоритета, истории посещений, соотношения клиентов и приглашенных партнеров самим салоном")

    user_salon_id = client_data.initial_salon_id
    user_salon = PartnerInfo.objects.get(id=user_salon_id)
    user_salon_city_id = user_salon.city_id

    # --- Получаем список ID всех салонов, с которыми взаимодействовал клиент ---
    excluded_salon_ids = [status.salon.id for status in client_data.clientsalonstatus_set.all()]

    # --- Получаем список ID всех категорий, с которыми взаимодействовал клиент ---
    excluded_category_ids = list({
        category.id
        for salon_id in excluded_salon_ids
        for category in PartnerInfo.objects.get(id=salon_id).categories.all()
    })

    # --- Проверяем наличие приоритетного салона для этого города, исключая неподходящие ---
    priority_salons_city = PartnerInfo.objects.filter(
        city_id=user_salon_city_id,
        id__in=excluded_salon_ids,
        categories__id__in=excluded_category_ids,
        priority=True
    ).exclude(id__in=excluded_salon_ids).exclude(categories__id__in=excluded_category_ids).all()

    if priority_salons_city:
        chosen_salon = random.choice(priority_salons_city)
        logger.info(f"Найден приоритетный салон в городе клиента: {chosen_salon.name}")
        return chosen_salon, True

    # --- Проверяем наличие связанного салона, исключая неподходящие ---
    if user_salon.linked_partner_id and user_salon.linked_partner_id not in excluded_salon_ids:
        try:
            linked_salon = PartnerInfo.objects.get(id=user_salon.linked_partner_id)
            if linked_salon and not any(category.id in excluded_category_ids for category in linked_salon.categories.all()):
                logger.info(f"Найден связанный салон: {linked_salon.name}")
                return linked_salon, False
        except PartnerInfo.DoesNotExist:
            pass  # Пропускаем, если связанный салон не найден

    # --- Приоритетные салоны, исключая неподходящие ---
    priority_salons = PartnerInfo.objects.filter(
        city_id=user_salon_city_id,
        priority=True
    ).exclude(id__in=excluded_salon_ids).exclude(categories__id__in=excluded_category_ids).all()

    if priority_salons:
        chosen_salon = random.choice(priority_salons)
        return chosen_salon, True

    # --- Доступные салоны, исключая неподходящие ---
    available_salons = PartnerInfo.objects.filter(
        city_id=user_salon_city_id
    ).exclude(id__in=excluded_salon_ids).exclude(categories__id__in=excluded_category_ids).all()

    if not available_salons:
        logger.error(
            f"Не удалось найти доступные салоны в городе {user_salon_city_id}, кроме взаимодействовавших с клиентом салонов")
        return None

    # --- Получаем настройки весов ---
    weight_settings = DiscountWeightSettings.objects.first()
    if not weight_settings:
        logger.error("Настройки весов не найдены!")
        return None

    # --- Соотношение "привел/получил" ---
    weighted_salons: List[PartnerInfo] = []
    for salon in available_salons:
        # --- Измененная формула расчета ratio ---
        ratio = salon.clients_brought / salon.clients_received if salon.clients_received > 0 else float('inf')
        # --- Инвертированная логика весов ---
        if 0.4 <= ratio <= 0.8:
            weight = weight_settings.ratio_below_30_weight
        elif 0.3 <= ratio < 0.4:
            weight = weight_settings.ratio_30_40_weight
        else:
            weight = weight_settings.ratio_40_80_weight

        weighted_salons.extend([salon] * weight)

    if weighted_salons:
        chosen_salon = random.choice(weighted_salons)
        return chosen_salon, False
    else:
        logger.error(f"Не удалось найти доступные салоны в городе {user_salon.city}, кроме категорий {', '.join([category.name for category in user_salon.categories.all()])} и взаимодействовавших с клиентом салонов, с учетом соотношения клиентов")
        return None    