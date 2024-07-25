from django.urls import path
from . import views

app_name = 'sarafan_admin'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index, name='index'),
    path('salons/', views.salons_list, name='salons'),
    path('salons/create/', views.create_salon, name='create_salon'),
    path('salons/<str:salon_id>/edit/', views.edit_salon, name='edit_salon'),
    path('salons/<str:salon_id>/delete/', views.delete_salon, name='delete_salon'),
    path('partners/', views.partners_list, name='partners'),
    path('partners/create/', views.create_partner, name='create_partner'),
    path('partners/<int:partner_id>/edit/', views.edit_partner, name='edit_partner'),
    path('partners/<int:partner_id>/delete/', views.delete_partner, name='delete_partner'),
    path('message_templates/', views.message_templates_list, name='message_templates'),
    path('message_templates/create/', views.create_message_template, name='create_message_template'),
    path('message_templates/<int:template_id>/edit/', views.edit_message_template, name='edit_message_template'),
    path('message_templates/<int:template_id>/delete/', views.delete_message_template, name='delete_message_template'),
    path('discount_weight_settings/', views.discount_weight_settings_view, name='discount_weight_settings'),
    path('categories/', views.categories_list, name='categories'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
]