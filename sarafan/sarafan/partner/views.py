import asyncio
import random
import io
import string

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import RegistrationForm, LoginForm, EditSalonForm
from app.models import Partner, PartnerInfo, User, PartnerInvitation, MessageTemplate
from app.qr_code import generate_qr_code
from app.views import get_template_or_default

def escape_handlebars_braces(text):
    """Экранирует фигурные скобки в тексте для Handlebars."""
    text = text.replace('{', '{{')
    text = text.replace('}', '}}')
    return text

def login_view(request):
    """Представление для входа партнера."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = User.objects.filter(username=username).first()
            if user is not None and user.check_password(password):
                login(request, user)
                messages.success(request, 'Вы вошли в систему!')
                return redirect(reverse('partner:dashboard'))
            else:
                messages.error(request, 'Неверный логин или пароль.')
    else:
        form = LoginForm()
    return render(request, 'partner/login.html', {'form': form})

@login_required
def logout_view(request):
    """Представление для выхода партнера."""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect(reverse('partner:login'))

def register_view(request):
    """Представление для регистрации партнера."""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Генерация уникального ID партнера
            partner_id = generate_unique_salon_id(form.cleaned_data['city'].name)
            # Создание партнера
            new_partner_info = PartnerInfo.objects.create(
                id=partner_id,
                partner_type=form.cleaned_data['partner_type'],
                name=form.cleaned_data['salon_name'],
                discount=form.cleaned_data['discount_text'],
                city=form.cleaned_data['city'],
                contacts=form.cleaned_data['contacts'],
                message_partner_name=form.cleaned_data['message_salon_name'],
                owner=form.cleaned_data['owner'] if form.cleaned_data['partner_type'] == 'individual' else None,
                invited_by=None
            )
            new_partner_info.categories.set(form.cleaned_data['categories'])
            # Генерация уникального кода
            unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            # Создание записи в таблице Partner
            new_partner = Partner.objects.create(
                user=user,
                salon=new_partner_info,
                referral_link=f"https://{request.get_host()}/partner/register?ref={user.id}",
                unique_code=unique_code
            )
            # Обработка реферальной ссылки
            ref_id = request.GET.get('ref')
            if ref_id:
                try:
                    inviting_partner = Partner.objects.get(user_id=ref_id)
                    new_partner_info.invited_by = inviting_partner.salon
                    inviting_partner.partners_invited += 1
                    inviting_partner.save()
                    # Создаем запись в таблице partner_invitations
                    PartnerInvitation.objects.create(inviting_partner=inviting_partner, invited_partner=new_partner)
                except Partner.DoesNotExist:
                    pass
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect(reverse('partner:login'))
    else:
        form = RegistrationForm()
    return render(request, 'partner/register.html', {'form': form})

def generate_unique_salon_id(city_name):
    """Генерирует уникальный ID салона на основе названия города
    """
    while True:
        city_letter = city_name[0].lower()
        salon_id = f"{city_letter}{random.randint(100000, 999999)}"

        # Проверяем, существует ли ID в базе данных
        if not PartnerInfo.objects.filter(id=salon_id).exists():
            # ID уникален, можно использовать
            return salon_id

@login_required
def dashboard_view(request):
    """Представление для личного кабинета партнера."""
    partner = get_object_or_404(Partner, user=request.user)
    salon = partner.salon
    edit_form = EditSalonForm(instance=salon)

    if request.method == 'POST' and edit_form.is_valid():
        edit_form.save()
        messages.success(request, 'Данные партнера успешно обновлены!')
        return redirect(reverse('partner:dashboard'))

    # --- Получаем образцы сообщений ---
    sample_messages = {}
    for template_name in ['get_discount_message', 'discount_offer']:
        sample_messages[template_name] = asyncio.run(get_template_or_default(
            template_name,
            discount=salon.discount,
            salon_name=salon.name,
            contacts=salon.contacts,
            message_salon_name=salon.message_partner_name,
            categories=", ".join([category.name for category in salon.categories.all()]),
            attempts_left=1
        ))

    # --- Получаем шаблоны сообщений из базы данных ---
    get_discount_message_template = escape_handlebars_braces(MessageTemplate.objects.get(name='get_discount_message').template).replace('\n', '\\n')
    discount_offer_template = escape_handlebars_braces(MessageTemplate.objects.get(name='discount_offer').template).replace('\n', '\\n')

    return render(request, 'partner/dashboard.html', {
        'partner': partner,
        'salon': salon,
        'edit_form': edit_form,
        'sample_messages': sample_messages,
        'get_discount_message_template': get_discount_message_template,
        'discount_offer_template': discount_offer_template
    })

@login_required
def qr_code_view(request):
    """Генерирует QR-код и возвращает его пользователю."""
    partner = get_object_or_404(Partner, user=request.user)
    data = f"https://wa.me/79933062088?text=Получить подарок ({partner.salon.id})"
    img = generate_qr_code(data)

    return FileResponse(
        io.BytesIO(img),
        as_attachment=True,
        filename='qr_code.png',
        content_type='image/png'
    )