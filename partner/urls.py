from django.urls import path
from . import views

app_name = 'partner'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/qr_code/', views.qr_code_view, name='qr_code'),
]