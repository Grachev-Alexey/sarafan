from django.db import models
from django.contrib.auth.models import AbstractUser
from partner.models import Partner

class City(models.Model):
    """Модель для хранения информации о городах."""
    name = models.CharField("Название города", max_length=255, unique=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    """Модель для хранения категорий салонов."""
    name = models.CharField("Название категории", max_length=255, unique=True)

    def __str__(self):
        return self.name

class PartnerInfo(models.Model):
    """Модель для хранения информации о партнерах."""
    id = models.CharField("ID партнера", max_length=255, primary_key=True)
    partner_type = models.CharField("Тип партнера", max_length=255)
    categories = models.ManyToManyField(Category, verbose_name="Категории")
    name = models.CharField("Название салона/мастера", max_length=255)
    discount = models.TextField("Текст оффера")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")
    contacts = models.CharField("Контактные данные", max_length=255)
    clients_brought = models.IntegerField("Привел клиентов", default=0)
    clients_received = models.IntegerField("Получил клиентов", default=0)
    priority = models.BooleanField("Приоритетный партнер", default=False)
    linked_partner_id = models.CharField("ID связанного партнера", max_length=255, null=True, blank=True)
    message_partner_name = models.CharField("Название салона/мастера для сообщений", max_length=255, null=True, blank=True)
    owner = models.CharField("Имя владельца (для частных мастеров)", max_length=255, null=True, blank=True)
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пригласивший партнер")

    def __str__(self):
        return f"PartnerInfo(id='{self.id}', name='{self.name}', categories='{self.categories}', city='{self.city}', linked_partner_id='{self.linked_partner_id}', message_partner_name='{self.message_partner_name}')"

class ClientsData(models.Model):
    """Модель для хранения данных о клиентах."""
    chat_id = models.CharField("ID чата", max_length=255, unique=True)
    initial_salon_name = models.CharField("Название салона, с которого пришел клиент", max_length=255)
    initial_salon_id = models.CharField("ID салона, с которого пришел клиент", max_length=255)
    claimed_salon_name = models.CharField("Название салона, в котором запрошена скидка", max_length=255, null=True, blank=True)
    claimed_salon_id = models.CharField("ID салона, в котором запрошена скидка", max_length=255, null=True, blank=True)
    chosen_salon_name = models.CharField("Название выбранного салона", max_length=255, null=True, blank=True)
    chosen_salon_id = models.CharField("ID выбранного салона", max_length=255, null=True, blank=True)
    client_name = models.CharField("Имя клиента", max_length=255)
    city = models.CharField("Город клиента", max_length=255, null=True, blank=True)
    discount_claimed = models.BooleanField("Скидка запрошена", default=False)
    attempts_left = models.IntegerField("Осталось попыток", default=1)

    def __str__(self):
        return f"ClientsData(chat_id='{self.chat_id}', initial_salon_name='{self.initial_salon_name}', claimed_salon_name='{self.claimed_salon_name}')"


class ClientSalonStatus(models.Model):
    """Модель для хранения статусов клиентов по отношению к салонам."""
    client = models.ForeignKey(ClientsData, on_delete=models.CASCADE, verbose_name="Клиент")
    salon = models.ForeignKey(PartnerInfo, on_delete=models.CASCADE, verbose_name="Салон")
    status = models.CharField("Статус", max_length=255)

    class Meta:
        unique_together = ('client', 'salon')

    def __str__(self):
        return f"ClientSalonStatus(client_id='{self.client.id}', salon_id='{self.salon.id}', status='{self.status}')"


class MessageTemplate(models.Model):
    """Модель для хранения шаблонов сообщений."""
    name = models.CharField("Название шаблона", max_length=255, unique=True)
    template = models.TextField("Шаблон сообщения")

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Модель пользователя, наследующая от AbstractUser Django."""
    pass


class PartnerInvitation(models.Model):
    """Модель для хранения информации о приглашениях партнеров."""
    inviting_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="invites_sent", verbose_name="Приглашающий партнер")
    invited_partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="invites_received", verbose_name="Приглашенный партнер")

    class Meta:
        unique_together = ('inviting_partner', 'invited_partner')


class DiscountWeightSettings(models.Model):
    """Модель для хранения настроек весов скидок."""
    ratio_40_80_weight = models.IntegerField("Вес для соотношения 40-80%", default=3)
    ratio_30_40_weight = models.IntegerField("Вес для соотношения 30-40%", default=2)
    ratio_below_30_weight = models.IntegerField("Вес для соотношения менее 30%", default=1)
    partners_invited_weight = models.IntegerField("Вес за каждого приглашенного партнера", default=1)