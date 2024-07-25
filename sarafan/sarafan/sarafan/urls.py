from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('partner/', include('app.partner.urls', namespace='partner')),
    path('', include('app.urls')),
]