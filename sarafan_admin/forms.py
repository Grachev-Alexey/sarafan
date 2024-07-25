from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import PartnerInfo, MessageTemplate, Partner, DiscountWeightSettings, Category, City

class SalonForm(forms.ModelForm):
    """Форма для управления салонами."""
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Категории",
        required=True
    )
    city = forms.ModelChoiceField(queryset=City.objects.all(), label="Город", required=True)

    class Meta:
        model = PartnerInfo
        fields = [
            'id', 'partner_type', 'categories', 'name', 'discount', 'city',
            'contacts', 'priority', 'linked_partner_id', 'message_partner_name', 'owner',
            'invited_by'
        ]

    def clean_owner(self):
        """Валидация поля owner."""
        partner_type = self.cleaned_data.get('partner_type')
        owner = self.cleaned_data.get('owner')

        if partner_type == 'individual' and not owner:
            raise forms.ValidationError('Пожалуйста, укажите имя владельца.')

        return owner

class PartnerForm(forms.ModelForm):
    """Форма для управления партнерами."""
    login = forms.CharField(label='Логин', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль', required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Подтвердите пароль', required=False)
    salon_id = forms.ModelChoiceField(queryset=PartnerInfo.objects.all(), label='Салон', required=True)

    class Meta:
        model = Partner
        fields = [
            'login', 'password', 'confirm_password', 'salon_id', 'referral_link',
            'clients_brought', 'clients_received', 'partners_invited',
        ]

    def clean(self):
        """Дополнительная валидация формы."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Пароли не совпадают.")

        return cleaned_data

    def save(self, commit=True):
        """Сохранение формы с обновлением пароля пользователя."""
        partner = super().save(commit=False)
        user = partner.user
        user.username = self.cleaned_data['login']
        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        user.save()
        if commit:
            partner.save()
        return partner

class MessageTemplateForm(forms.ModelForm):
    """Форма для управления шаблонами сообщений."""

    class Meta:
        model = MessageTemplate
        fields = ['name', 'template']

class DiscountWeightSettingsForm(forms.ModelForm):
    """Форма для управления настройками весов скидок."""

    class Meta:
        model = DiscountWeightSettings
        fields = ['ratio_40_80_weight', 'ratio_30_40_weight', 'ratio_below_30_weight', 'partners_invited_weight']

class CategoryForm(forms.ModelForm):
    """Форма для управления категориями."""

    class Meta:
        model = Category
        fields = ['name']

class sarafan_adminLoginForm(forms.Form):
    """Форма для входа администратора."""
    username = forms.CharField(label='Логин', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль', required=True)