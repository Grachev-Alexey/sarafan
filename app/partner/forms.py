from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, HiddenField, SelectMultipleField, RadioField, IntegerField
from wtforms.widgets import ListWidget, HiddenInput
from wtforms.validators import DataRequired, Length, EqualTo, Optional, InputRequired, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField

from app.models import Category, City

class RegistrationForm(FlaskForm):
    salon_name = StringField('Название салона/мастера', validators=[DataRequired()])
    categories = QuerySelectMultipleField(
        'Категории',
        query_factory=lambda: Category.query.all(),
        get_label='name',
        allow_blank=False
    )
    city = QuerySelectField('Город', query_factory=lambda: City.query.all(), get_label='name', allow_blank=False)
    discount_text = TextAreaField('Текст оффера', validators=[DataRequired()])
    contacts = StringField('Контактные данные', validators=[DataRequired()])
    message_salon_name = StringField('Название салона/мастера для сообщений', validators=[DataRequired()])
    login = StringField('Логин', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6, max=30),
                                                    EqualTo('confirm_password', message='Пароли должны совпадать')])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired()])
    partner_type = RadioField('Тип партнера', choices=[('salon', 'Салон'), ('individual', 'Частный мастер')], validators=[InputRequired()])

    def validate_owner(self, field):
        """Валидация  owner."""
        if self.partner_type.data == 'individual' and not field.data:
            raise ValidationError('Пожалуйста, укажите имя владельца')

    owner = StringField('Имя владельца (для частных мастеров)', validators=[validate_owner])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class EditSalonForm(FlaskForm):
    salon_name = StringField('Название салона/мастера', validators=[DataRequired()])
    categories = QuerySelectMultipleField(
        'Категории',
        query_factory=lambda: Category.query.all(),
        get_label='name',
        allow_blank=False
    )
    city = QuerySelectField('Город', query_factory=lambda: City.query.all(), get_label='name', allow_blank=False)
    discount = TextAreaField('Текст скидки', validators=[DataRequired()])
    contacts = StringField('Контактные данные', validators=[DataRequired()])
    message_salon_name = StringField('Название салона/мастера для сообщений', validators=[DataRequired()])
    partner_type = RadioField('Тип партнера', choices=[('salon', 'Салон'), ('individual', 'Частный мастер')], validators=[InputRequired()])
    owner = StringField('Имя владельца (для частных мастеров)', validators=[Optional(), DataRequired('Пожалуйста, укажите имя владельца')])
    telegram_chat_id = IntegerField('Telegram ID')
    salon_id = HiddenField('salon_id')
    submit = SubmitField('Сохранить изменения')