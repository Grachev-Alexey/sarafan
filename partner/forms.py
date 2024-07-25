from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Partner, PartnerInfo, Category, City

class RegistrationForm(UserCreationForm):
    """Форма для регистрации партнера."""
    salon_name = forms.CharField(label='Название салона/мастера', required=True)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Категории',
        required=True
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), label='Город', required=True)
    discount_text = forms.CharField(widget=forms.Textarea, label='Текст оффера', required=True)
    contacts = forms.CharField(label='Контактные данные', required=True)
    message_salon_name = forms.CharField(label='Название салона/мастера для сообщений', required=True)
    partner_type = forms.ChoiceField(
        choices=[('salon', 'Салон'), ('individual', 'Частный мастер')],
        widget=forms.RadioSelect,
        label='Тип партнера',
        required=True
    )
    owner = forms.CharField(label='Имя владельца (для частных мастеров)', required=False)

    def clean_owner(self):
        """Валидация поля owner."""
        partner_type = self.cleaned_data.get('partner_type')
        owner = self.cleaned_data.get('owner')

        if partner_type == 'individual' and not owner:
            raise forms.ValidationError('Пожалуйста, укажите имя владельца.')

        return owner

class LoginForm(forms.Form):
    """Форма для входа партнера."""
    username = forms.CharField(label='Логин', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль', required=True)

class EditSalonForm(forms.ModelForm):
    """Форма для редактирования данных салона."""
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Категории',
        required=True
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), label='Город', required=True)

    class Meta:
        model = PartnerInfo
        fields = [
            'salon_name', 'partner_type', 'categories', 'city', 'discount', 'contacts',
            'message_salon_name', 'owner'
        ]

    def clean_owner(self):
        """Валидация поля owner."""
        partner_type = self.cleaned_data.get('partner_type')
        owner = self.cleaned_data.get('owner')

        if partner_type == 'individual' and not owner:
            raise forms.ValidationError('Пожалуйста, укажите имя владельца.')

        return owner