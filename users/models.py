from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    ROLES = [
        ('admin', 'admin'),
        ('moderator', 'moderator'),
        ('aspirant', 'aspirant'),
        ('observer', 'observer'),
    ]
    PLATFORMS = [
        ('range', 'range'),
        ('simulation', 'simulation'),
    ]
    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('NA', 'NA')
    ]
    ASPIRANT_ROLES = [
        ('blue', 'blue'),
        ('red', 'red'),
        ('ctf', 'ctf'),
        ('red_vs_blue', 'red_vs_blue')
    ]


    email = models.EmailField(_('email address'), unique=True, blank=False, null=False)
    username = models.CharField(max_length=150, unique=True)
    platform = models.CharField(max_length=150, null=False,blank=False,default='range')
    phone = models.CharField(max_length=20, null=False, blank=False)
    role = models.CharField(max_length=20, choices=ROLES, default='aspirant')
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    image = models.ImageField(default='default-avatar.png', upload_to='user_avatars')
    gender = models.CharField(max_length=8, choices=GENDER, default='NA')
    aspirant_role = models.CharField(max_length=50, choices=ASPIRANT_ROLES, default='NA')
    city = models.CharField(max_length=150, null=False, blank=False,default='NA')
    first_name = models.CharField(max_length=150, null=False, blank=False,default='NA')
    dob = models.DateTimeField(max_length=80, null=False, blank=False,default=timezone.now)
    is_terms_accepted = models.BooleanField(default=False)
    # is_previously_logged_in = models.BooleanField(default=False)
    # USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'role','platform']

    def __str__(self):
        return self.email



    class Meta:
        # unique_together = ('username', 'company',)
        db_table = 'auth_user'

