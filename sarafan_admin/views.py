from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from .forms import SalonForm, PartnerForm, MessageTemplateForm, DiscountWeightSettingsForm, CategoryForm, sarafan_adminLoginForm
from app.models import PartnerInfo, MessageTemplate, Partner, User, DiscountWeightSettings, ClientsData, Category, City

def sarafan_admin_required(view_func):
    """Декоратор для проверки, что пользователь является администратором."""
    decorated_view_func = user_passes_test(lambda u: u.is_superuser, login_url='sarafan_admin:login')(view_func)
    return decorated_view_func

def login_view(request):
    """Представление для входа администратора."""
    if request.method == 'POST':
        form = sarafan_adminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = User.objects.filter(username=username).first()
            if user is not None and user.check_password(password):
                login(request, user)
                messages.success(request, 'Вы вошли как администратор!')
                return redirect(reverse('sarafan_admin:index'))
            else:
                messages.error(request, 'Неверный логин или пароль.')
    else:
        form = sarafan_adminLoginForm()
    return render(request, 'sarafan_admin/login.html', {'form': form})

def logout_view(request):
    """Представление для выхода администратора."""
    logout(request)
    return redirect(reverse('sarafan_admin:login'))

@sarafan_admin_required
def index(request):
    """Представление для главной страницы админки."""
    salon_count = PartnerInfo.objects.count()
    partner_count = Partner.objects.count()
    client_count = ClientsData.objects.count()
    return render(request, 'sarafan_admin/dashboard.html', {
        'salon_count': salon_count,
        'partner_count': partner_count,
        'client_count': client_count,
    })

@sarafan_admin_required
def salons_list(request):
    """Представление для списка салонов."""
    salons = PartnerInfo.objects.all()
    return render(request, 'sarafan_admin/salons.html', {'salons': salons})

@sarafan_admin_required
def create_salon(request):
    """Представление для создания салона."""
    if request.method == 'POST':
        form = SalonForm(request.POST)
        if form.is_valid():
            salon = form.save(commit=False)  # Не сохраняем сразу
            salon.save()  # Сохраняем салон, чтобы получить ID
            form.save_m2m()  # Сохраняем связи many-to-many
            messages.success(request, 'Партнер успешно добавлен!')
            return redirect(reverse('sarafan_admin:salons'))
    else:
        form = SalonForm()
    return render(request, 'sarafan_admin/edit_salon.html', {'form': form, 'title': 'Добавить партнера'})

@sarafan_admin_required
def edit_salon(request, salon_id):
    """Представление для редактирования салона."""
    salon = get_object_or_404(PartnerInfo, id=salon_id)
    if request.method == 'POST':
        form = SalonForm(request.POST, instance=salon)
        if form.is_valid():
            salon = form.save(commit=False)
            salon.save()
            form.save_m2m()  # Сохраняем связи many-to-many
            partner = Partner.objects.filter(salon=salon).first()
            if partner:
                partner.salon_id = form.cleaned_data['id']
                partner.save()
            messages.success(request, 'Партнер успешно обновлен!')
            return redirect(reverse('sarafan_admin:edit_salon', args=[salon.id]))
    else:
        form = SalonForm(instance=salon)
    return render(request, 'sarafan_admin/edit_salon.html', {'form': form, 'title': 'Редактировать партнера', 'enumerate': enumerate})

@sarafan_admin_required
def delete_salon(request, salon_id):
    """Представление для удаления салона."""
    salon = get_object_or_404(PartnerInfo, id=salon_id)
    salon.delete()
    messages.success(request, 'Партнер успешно удален!')
    return redirect(reverse('sarafan_admin:salons'))

@sarafan_admin_required
def partners_list(request):
    """Представление для списка партнеров."""
    partners = Partner.objects.all()
    return render(request, 'sarafan_admin/partners.html', {'partners': partners})

@sarafan_admin_required
def create_partner(request):
    """Представление для создания партнера."""
    if request.method == 'POST':
        form = PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save(commit=False) # Не сохраняем сразу
            partner.save() # Сохраняем партнера
            messages.success(request, 'Партнер успешно добавлен!')
            return redirect(reverse('sarafan_admin:partners'))
    else:
        form = PartnerForm()
    return render(request, 'sarafan_admin/edit_partner.html', {'form': form, 'title': 'Добавить партнера'})

@sarafan_admin_required
def edit_partner(request, partner_id):
    """Представление для редактирования партнера."""
    partner = get_object_or_404(Partner, id=partner_id)
    user = partner.user
    if request.method == 'POST':
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            # Обновляем данные салона
            salon = partner.salon
            salon.clients_brought = partner.clients_brought
            salon.clients_received = partner.clients_received
            salon.save()
            messages.success(request, 'Партнер успешно обновлен!')
            return redirect(reverse('sarafan_admin:partners'))
    else:
        # Инициализируем поле login
        form = PartnerForm(instance=partner, initial={'login': user.username})
    return render(request, 'sarafan_admin/edit_partner.html', {'form': form, 'user': user, 'title': 'Редактировать партнера'})

@sarafan_admin_required
def delete_partner(request, partner_id):
    """Представление для удаления партнера."""
    partner = get_object_or_404(Partner, id=partner_id)
    user = partner.user
    user.delete()
    messages.success(request, 'Партнер успешно удален!')
    return redirect(reverse('sarafan_admin:partners'))

@sarafan_admin_required
def message_templates_list(request):
    """Представление для списка шаблонов сообщений."""
    templates = MessageTemplate.objects.all()
    return render(request, 'sarafan_admin/message_templates.html', {'message_templates': templates})

@sarafan_admin_required
def create_message_template(request):
    """Представление для создания шаблона сообщения."""
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Шаблон сообщения успешно добавлен!')
            return redirect(reverse('sarafan_admin:message_templates'))
    else:
        form = MessageTemplateForm()
    return render(request, 'sarafan_admin/edit_message_template.html', {'form': form, 'title': 'Добавить шаблон сообщения'})

@sarafan_admin_required
def edit_message_template(request, template_id):
    """Представление для редактирования шаблона сообщения."""
    template = get_object_or_404(MessageTemplate, id=template_id)
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Шаблон сообщения успешно обновлен!')
            return redirect(reverse('sarafan_admin:message_templates'))
    else:
        form = MessageTemplateForm(instance=template)
    return render(request, 'sarafan_admin/edit_message_template.html', {'form': form, 'title': 'Редактировать шаблон сообщения'})

@sarafan_admin_required
def delete_message_template(request, template_id):
    """Представление для удаления шаблона сообщения."""
    template = get_object_or_404(MessageTemplate, id=template_id)
    template.delete()
    messages.success(request, 'Шаблон сообщения успешно удален!')
    return redirect(reverse('sarafan_admin:message_templates'))

@sarafan_admin_required
def discount_weight_settings_view(request):
    """Представление для настроек весов скидок."""
    settings, created = DiscountWeightSettings.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = DiscountWeightSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки весов успешно сохранены!')
            return redirect(reverse('sarafan_admin:discount_weight_settings'))
    else:
        form = DiscountWeightSettingsForm(instance=settings)
    return render(request, 'sarafan_admin/edit_discount_weight_settings.html', {'form': form, 'title': 'Настройки весов скидок'})

@sarafan_admin_required
def categories_list(request):
    """Представление для списка категорий."""
    categories = Category.objects.all()
    return render(request, 'sarafan_admin/categories.html', {'categories': categories})

@sarafan_admin_required
def create_category(request):
    """Представление для создания категории."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно добавлена!')
            return redirect(reverse('sarafan_admin:categories'))
    else:
        form = CategoryForm()
    return render(request, 'sarafan_admin/edit_category.html', {'form': form, 'title': 'Добавить категорию'})

@sarafan_admin_required
def edit_category(request, category_id):
    """Представление для редактирования категории."""
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно обновлена!')
            return redirect(reverse('sarafan_admin:categories'))
    else:
        form = CategoryForm(instance=category)
    return render(request, 'sarafan_admin/edit_category.html', {'form': form, 'title': 'Редактировать категорию'})

@sarafan_admin_required
def delete_category(request, category_id):
    """Представление для удаления категории."""
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Категория успешно удалена!')
    return redirect(reverse('sarafan_admin:categories'))