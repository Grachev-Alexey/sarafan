from django.contrib import admin
from .models import PartnerInfo, ClientsData, ClientSalonStatus, MessageTemplate, User, Partner, PartnerInvitation, DiscountWeightSettings, Category, City

# Регистрируем модели в админке
admin.site.register(PartnerInfo)
admin.site.register(ClientsData)
admin.site.register(ClientSalonStatus)
admin.site.register(MessageTemplate)
admin.site.register(User)
admin.site.register(Partner)
admin.site.register(PartnerInvitation)
admin.site.register(DiscountWeightSettings)
admin.site.register(Category)
admin.site.register(City)