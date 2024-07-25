from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, login_user, logout_user
from app.models import PartnerInfo, MessageTemplate, Partner, User, DiscountWeightSettings, ClientsData, Category, City
from app.admin.forms import SalonForm, PartnerForm, MessageTemplateForm, DiscountWeightSettingsForm, CategoryForm, AdminLoginForm
from app import db
from urllib.parse import urlparse

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'admin':
            flash('У вас нет доступа к этой странице.', 'error')
            return redirect(url_for('admin.login'))
        return func(*args, **kwargs)
    return decorated_view

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль', 'danger')
            return redirect(url_for('admin.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('admin.index')
        return redirect(next_page)
    return render_template('admin/login.html', title='Вход', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@bp.route('/')
@admin_required
def index():
    salon_count = PartnerInfo.query.count()
    partner_count = Partner.query.count()
    client_count = ClientsData.query.count()
    return render_template('admin/dashboard.html', salon_count=salon_count, partner_count=partner_count, client_count=client_count)

@bp.route('/salons')
@admin_required
def salons():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    salons = PartnerInfo.query.all()
    return render_template('admin/salons.html', salons=salons)

@bp.route('/salons/create', methods=['GET', 'POST'])
@admin_required
def create_salon():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    form = SalonForm()
    if form.validate_on_submit():
        salon = PartnerInfo(**form.data)
        salon.categories = form.categories.data
        salon.city_id = form.city.data.id
        db.session.add(salon)
        db.session.commit()
        flash('Партнер успешно добавлен!', 'success')
        return redirect(url_for('admin.salons'))
    return render_template('admin/edit_salon.html', form=form, title='Добавить партнера')

@bp.route('/salons/<salon_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_salon(salon_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    salon = PartnerInfo.query.get_or_404(salon_id)
    form = SalonForm(obj=salon)
    if form.validate_on_submit():
        try:
            with db.session.begin_nested():
                form.populate_obj(salon)
                salon.categories = form.categories.data
                salon.city_id = form.city.data.id
                partner = Partner.query.filter_by(salon_id=salon_id).first()
                if partner:
                    partner.salon_id = form.id.data
                    partner.telegram_chat_id = form.telegram_chat_id.data
            db.session.commit()
            flash('Партнер успешно обновлен!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении партнера: {e}', 'error')
        return redirect(url_for('admin.edit_salon', salon_id=salon.id))
    return render_template('admin/edit_salon.html', form=form, title='Редактировать партнера', enumerate=enumerate)

@bp.route('/salons/<salon_id>/delete', methods=['POST'])
@admin_required
def delete_salon(salon_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    salon = PartnerInfo.query.get_or_404(salon_id) 
    db.session.delete(salon)
    db.session.commit()
    flash('Партнер успешно удален!', 'success')
    return redirect(url_for('admin.salons'))

@bp.route('/partners')
@admin_required
def partners():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    partners = Partner.query.all()
    return render_template('admin/partners.html', partners=partners)

@bp.route('/partners/create', methods=['GET', 'POST'])
@admin_required
def create_partner():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    form = PartnerForm()
    form.salon_id.choices = [(str(salon.id), salon.name) for salon in PartnerInfo.query.all()]
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.login.data).first()
        if user is None:
            user = User(username=form.login.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

        partner = Partner(
            user_id=user.id,
            salon_id=form.salon_id.data,
            referral_link=form.referral_link.data,
            clients_brought=form.clients_brought.data,
            clients_received=form.clients_received.data,
            partners_invited=form.partners_invited.data,
            telegram_chat_id=form.telegram_chat_id.data
        )
        db.session.add(partner)
        db.session.commit()
        flash('Партнер успешно добавлен!', 'success')
        return redirect(url_for('admin.partners'))
    return render_template('admin/edit_partner.html', form=form, title='Добавить партнера')

@bp.route('/partners/<partner_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_partner(partner_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    partner = Partner.query.get_or_404(partner_id)
    user = User.query.get(partner.user_id)
    form = PartnerForm(obj=partner)
    form.salon_id.choices = [(str(salon.id), salon.name) for salon in PartnerInfo.query.all()]
    if form.validate_on_submit():
        user.username = form.login.data
        if form.password.data:
            user.set_password(form.password.data)

        form.populate_obj(partner)
        partner.telegram_chat_id = form.telegram_chat_id.data

        # Обновляем данные салона
        salon = PartnerInfo.query.get(partner.salon_id)
        salon.clients_brought = partner.clients_brought
        salon.clients_received = partner.clients_received

        db.session.commit()  # Сохраняем все изменения
        flash('Партнер успешно обновлен!', 'success')
        return redirect(url_for('admin.partners'))
    return render_template('admin/edit_partner.html', form=form, user=user, title='Редактировать партнера')

@bp.route('/partners/<partner_id>/delete', methods=['POST'])
@admin_required
def delete_partner(partner_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    partner = Partner.query.get_or_404(partner_id)
    user = User.query.get(partner.user_id)
    db.session.delete(partner)
    db.session.delete(user)
    db.session.commit()
    flash('Партнер успешно удален!', 'success')
    return redirect(url_for('admin.partners'))    

@bp.route('/message_templates')
@admin_required
def message_templates():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    message_templates = MessageTemplate.query.all()
    return render_template('admin/message_templates.html', message_templates=message_templates)

@bp.route('/message_templates/create', methods=['GET', 'POST'])
@admin_required
def create_message_template():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    form = MessageTemplateForm()
    if form.validate_on_submit():
        template = MessageTemplate(
            name=form.name.data,
            template=form.template.data
        )
        db.session.add(template)
        db.session.commit()
        flash('Шаблон сообщения успешно добавлен!', 'success')
        return redirect(url_for('admin.message_templates'))
    return render_template('admin/edit_message_template.html', form=form, title='Добавить шаблон сообщения')

@bp.route('/message_templates/<template_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_message_template(template_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    template = MessageTemplate.query.get_or_404(template_id)
    form = MessageTemplateForm(obj=template)
    if form.validate_on_submit():
        form.populate_obj(template)
        db.session.commit()
        flash('Шаблон сообщения успешно обновлен!', 'success')
        return redirect(url_for('admin.message_templates'))
    return render_template('admin/edit_message_template.html', form=form, title='Редактировать шаблон сообщения')

@bp.route('/message_templates/<template_id>/delete', methods=['POST'])
@admin_required
def delete_message_template(template_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    template = MessageTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash('Шаблон сообщения успешно удален!', 'success')
    return redirect(url_for('admin.message_templates'))

@bp.route('/discount_weight_settings', methods=['GET', 'POST'])
@admin_required
def discount_weight_settings():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    settings = DiscountWeightSettings.query.get_or_404(1)
    form = DiscountWeightSettingsForm(obj=settings)
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('Настройки весов успешно сохранены!', 'success')
        return redirect(url_for('admin.discount_weight_settings'))
    return render_template('admin/edit_discount_weight_settings.html', form=form, title='Настройки весов скидок')   
    
@bp.route('/categories')
@admin_required
def categories():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@bp.route('/categories/create', methods=['GET', 'POST'])
@admin_required
def create_category():
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data)
        db.session.add(category)
        db.session.commit()
        flash('Категория успешно добавлена!', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/edit_category.html', form=form, title='Добавить категорию')

@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        form.populate_obj(category)
        db.session.commit()
        flash('Категория успешно обновлена!', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/edit_category.html', form=form, title='Редактировать категорию')

@bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    if current_user.username != 'admin':
        flash('У вас нет доступа к этой странице.', 'error')
        return redirect(url_for('admin.login'))
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Категория успешно удалена!', 'success')
    return redirect(url_for('admin.categories'))    