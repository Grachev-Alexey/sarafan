from django.db import models
from django.contrib.auth.models import User
# Удаляем импорт PartnerInfo 

class Partner(models.Model):
    """Модель для хранения информации о партнерах, связанных с пользователем."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    salon = models.OneToOneField("app.PartnerInfo", on_delete=models.CASCADE, verbose_name="Салон")  # Используем строковый импорт
    referral_link = models.CharField("Реферальная ссылка", max_length=255, unique=True)
    clients_brought = models.IntegerField("Привел клиентов", default=0)
    clients_received = models.IntegerField("Получил клиентов", default=0)
    partners_invited = models.IntegerField("Пригласил партнеров", default=0)
    unique_code = models.CharField("Уникальный код", max_length=255, null=True, blank=True)

    def __str__(self):
        from app.models import PartnerInfo # Импортируем PartnerInfo здесь
        return f"Partner(id='{self.id}', salon_id='{self.salon.id}')"