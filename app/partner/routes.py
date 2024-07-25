import asyncio
import random
import io
import string
import os

from flask import render_template, redirect, url_for, flash, request, send_file
from app.partner import bp
from app.partner.forms import RegistrationForm, LoginForm, EditSalonForm
from app.models import Partner, PartnerInfo, User, PartnerInvitation, Category, City, MessageTemplate
from app import db
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.qr_code import generate_qr_code
from app.routes import get_template_or_default

# --- Функция для экранирования фигурных скобок ---
def escape_handlebars_braces(text):
    """Экранирует фигурные скобки в тексте для Handlebars."""
    text = text.replace('{', '{{')
    text = text.replace('}', '}}')
    return text

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.login.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы вошли в систему!', 'success')
            # Перенаправление на страницу личного кабинета
            return redirect(url_for('partner.dashboard'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    return render_template('partner/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('partner.login'))
    
@bp.route('/')
def index():
    return redirect(url_for('partner.dashboard'))    

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    ref_id = request.args.get('ref')
    if form.validate_on_submit():
        # Проверка, что логин не занят
        existing_user = User.query.filter_by(username=form.login.data).first()
        if existing_user:
            flash('Этот логин уже занят. Пожалуйста, выберите другой.', 'danger')
            return redirect(url_for('partner.register'))

        # Генерация уникального ID партнера
        partner_id = generate_unique_salon_id(form.city.data.name)

        # Создание пользователя
        new_user = User(username=form.login.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()

        # Создание партнера
        new_partner_info = PartnerInfo(
            id=partner_id,
            partner_type=form.partner_type.data,
            categories=form.categories.data,
            name=form.salon_name.data,
            discount=form.discount_text.data,
            city_id=form.city.data.id,
            contacts=form.contacts.data,
            message_partner_name=form.message_salon_name.data,
            owner=form.owner.data if form.partner_type.data == 'individual' else None,
            invited_by=None
        )
        db.session.add(new_partner_info)
        db.session.flush()

        db.session.commit()  # Сохраняем пользователя и партнера в базе данных

        # Генерация уникального кода
        unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Создание записи в таблице Partner
        new_partner = Partner(
            user_id=new_user.id,
            salon_id=new_partner_info.id,
            referral_link=f"https://{request.host}/partner/register?ref={new_user.id}",
            unique_code=unique_code # Сохраняем уникальный код
        )
        db.session.add(new_partner)
        db.session.commit()  # Сохраняем партнера в базе данных

        # Обработка реферальной ссылки
        if ref_id:
            inviting_partner = Partner.query.filter_by(user_id=ref_id).first()
            if inviting_partner:
                new_partner_info.invited_by = inviting_partner.id
                inviting_partner.partners_invited += 1

                # Создаем запись в таблице partner_invitations
                new_invitation = PartnerInvitation(inviting_partner_id=inviting_partner.id, invited_partner_id=new_partner.id)
                db.session.add(new_invitation)
                db.session.commit()  # Сохраняем приглашение

        # Инструкции для партнера
        flash(f'Регистрация прошла успешно! Чтобы подключить Telegram-оповещения, отправьте боту @{os.environ.get("TELEGRAM_BOT_USERNAME")} следующее сообщение: `/connect {unique_code}`', 'success')
        return redirect(url_for('partner.login'))

    return render_template('partner/register.html', form=form)

def generate_unique_salon_id(city_name):
    """Генерирует уникальный ID салона на основе названия города
    """
    while True:
        city_letter = city_name[0].lower()
        salon_id = f"{city_letter}{random.randint(100000, 999999)}"

        # Проверяем, существует ли ID в базе данных
        existing_salon = PartnerInfo.query.get(salon_id)
        if not existing_salon:
            # ID уникален, можно использовать
            return salon_id
    
@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    partner = Partner.query.filter_by(user_id=current_user.id).first()
    if not partner:
        flash('Вы не зарегистрированы как партнер.', 'danger')
        return redirect(url_for('partner.register'))

    partner_info = PartnerInfo.query.get(partner.salon_id)
    edit_form = EditSalonForm(obj=partner_info)

    if edit_form.validate_on_submit() and request.method == 'POST':
        partner_id = partner.salon_id
        partner_info = PartnerInfo.query.get(partner_id)
        if partner_info:
            # Обновляем  названия салона и названия для сообщений
            partner_info.name = edit_form.salon_name.data
            partner_info.message_partner_name = edit_form.message_salon_name.data
            partner_info.city_id = edit_form.city.data.id

            # Обновляем остальные 
            edit_form.populate_obj(partner_info)
            partner_info.categories = edit_form.categories.data
            partner.telegram_chat_id = edit_form.telegram_chat_id.data

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при сохранении данных: {e}")
                flash('Ошибка при обновлении данных.', 'danger')
            else:
                flash('Данные партнера успешно обновлены!', 'success')
            return redirect(url_for('partner.dashboard'))
        else:
            flash('Партнер не найден.', 'danger')
            return redirect(url_for('partner.dashboard'))

    # --- Получаем образцы сообщений ---
    sample_messages = {}
    for template_name in ['get_discount_message', 'discount_offer']:
        sample_messages[template_name] = asyncio.run(get_template_or_default(
            template_name,
            discount=partner_info.discount,
            salon_name=partner_info.name,
            contacts=partner_info.contacts,
            message_salon_name=partner_info.message_partner_name,
            categories=", ".join([category.name for category in partner_info.categories]),
            attempts_left=1 
        ))

    # --- Получаем шаблоны сообщений из базы данных ---
    get_discount_message_template = escape_handlebars_braces(MessageTemplate.query.filter_by(name='get_discount_message').first().template).replace('\n', '\\n')
    discount_offer_template = escape_handlebars_braces(MessageTemplate.query.filter_by(name='discount_offer').first().template).replace('\n', '\\n')

    return render_template('partner/dashboard.html',
                           partner=partner,
                           salon=partner_info,
                           edit_form=edit_form,
                           PartnerInfo=PartnerInfo,
                           sample_messages=sample_messages,
                           get_discount_message_template=get_discount_message_template,
                           discount_offer_template=discount_offer_template)

@bp.route('/dashboard/qr_code')
@login_required
def qr_code():
    """Генерирует QR-код и отправляет его пользователю."""
    partner = Partner.query.filter_by(user_id=current_user.id).first()
    if not partner:
        flash('Вы не зарегистрированы как партнер.', 'danger')
        return redirect(url_for('partner.register'))

    data = f"https://wa.me/79933062088?text=Получить подарок ({partner.salon_id})"
    img = generate_qr_code(data)

    return send_file(
        io.BytesIO(img),
        mimetype='image/png',
        as_attachment=True,
        download_name='qr_code.png'
    )