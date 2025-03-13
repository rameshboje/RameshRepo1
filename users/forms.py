from django.contrib.auth.forms import AuthenticationForm
from django import forms


class UserLoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'email', 'id': 'username','placeholder':'Username'})
    )
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'class': 'form-control',
            'id': 'password',
            'name': 'password',
            'placeholder':'Password',
        }
    ))
    platform = forms.CharField(widget=forms.TextInput(
        attrs={
            'class': 'hidden',
            'id': 'platform_id',
            'name': 'platform',
            'value':'Training',
        }
    ))

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        

