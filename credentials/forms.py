from django import forms
from credentials.models import Credential
from datetime import datetime
from django.core.validators import RegexValidator


class CredentialForm(forms.ModelForm):
    alphanumeric = RegexValidator(regex=r'^[a-zA-Z0-9!@#$&()\\`.+,/\-"]*$')
    ip_regex = RegexValidator(
        regex=r'^\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}$',
        message='Enter valid IP'
    )

    ip = forms.GenericIPAddressField(validators=[ip_regex], max_length=128)
    username = forms.CharField(validators=[alphanumeric], max_length=30)
    password = forms.CharField(validators=[alphanumeric], max_length=30)
    machine_name = forms.CharField(validators=[alphanumeric], max_length=30)
    snap_shot_name = forms.CharField(max_length=30)

    class Meta:
        model = Credential
        fields = ('ip','snap_shot_name', 'username', 'machine_name', 'password', 'is_reverted', 'machine_type')


class EditCredentialForm(forms.ModelForm):
    alphanumeric = RegexValidator(regex=r'^[a-zA-Z0-9!@#$&()\\`.+,/\-"]*$')

    username = forms.CharField(validators=[alphanumeric], max_length=30)
    password = forms.CharField(validators=[alphanumeric], max_length=30)
    machine_name = forms.CharField(max_length=30)
    

    class Meta:
        model = Credential
        fields = ('username', 'password', 'is_reverted', 'machine_type')
