from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, IntegerField, PasswordField, SelectMultipleField, RadioField, IntegerField 
from wtforms.widgets import ListWidget, HiddenInput
from wtforms.validators import DataRequired, Length, EqualTo, Optional, InputRequired
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from app.models import Category, City

class SalonForm(FlaskForm):
    id = StringField('ID', validators=[DataRequired()])
    partner_type = RadioField('Тип партнера', choices=[('salon', 'Салон'), ('individual', 'Частный мастер')], validators=[InputRequired()])
    categories = QuerySelectMultipleField(
        'Категории',
        query_factory=lambda: Category.query.all(),
        get_label='name',
        allow_blank=False
    )
    name = StringField('Название', validators=[DataRequired()])
    discount = TextAreaField('Оффер', validators=[DataRequired()])
    city = QuerySelectField('Город', query_factory=lambda: City.query.all(), get_label='name', allow_blank=False)
    contacts = StringField('Контакты', validators=[DataRequired()])
    priority = BooleanField('Приоритет')
    linked_partner_id = StringField('ID связанного партнера')
    message_partner_name = StringField('Название для сообщений')
    owner = StringField('Имя владельца (для частных мастеров)', validators=[Optional(), DataRequired('Пожалуйста, укажите имя владельца')])
    telegram_chat_id = IntegerField('Telegram ID')
    submit = SubmitField('Сохранить')
    
class PartnerForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[Optional(), Length(min=6, max=30), 
                                                    EqualTo('confirm_password', message='Пароли должны совпадать')])
    confirm_password = PasswordField('Подтвердите пароль', validators=[Optional()])
    salon_id = StringField('ID Салона', validators=[DataRequired()])
    referral_link = StringField('Реферальная ссылка', validators=[DataRequired()])
    clients_brought = IntegerField('Привел клиентов', validators=[DataRequired()])
    clients_received = IntegerField('Получил клиентов', validators=[DataRequired()])
    partners_invited = IntegerField('Приглашено партнеров', validators=[DataRequired()])
    telegram_chat_id = IntegerField('Telegram ID')
    submit = SubmitField('Сохранить')

class MessageTemplateForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    template = TextAreaField('Шаблон', validators=[DataRequired()])
    submit = SubmitField('Сохранить')
    
class DiscountWeightSettingsForm(FlaskForm):
    ratio_40_80_weight = IntegerField('Вес для соотношения 40-80%', validators=[DataRequired()])
    ratio_30_40_weight = IntegerField('Вес для соотношения 30-40%', validators=[DataRequired()])
    ratio_below_30_weight = IntegerField('Вес для соотношения менее 30%', validators=[DataRequired()])
    partners_invited_weight = IntegerField('Вес за каждого приглашенного партнера', validators=[DataRequired()])
    submit = SubmitField('Сохранить')    

class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    submit = SubmitField('Сохранить')    
    
class AdminLoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')    