from django.shortcuts import render
# from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.contrib.auth.views import RedirectURLMixin
from django.views.generic.edit import FormView
from .forms import UserLoginForm
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, login as auth_login,
)
from range_activity.models import CyberGameParticipants
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import resolve_url
from django.conf import settings
# from django.utils.http import is_safe_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.sites.shortcuts import get_current_site
from users.models import User
import json
from django.shortcuts import redirect
from django.contrib.auth.forms import PasswordChangeForm
from django.views import View
from django.contrib.auth.hashers import make_password, check_password
import re
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Import `logout` for logging out users.
from django.contrib.auth import logout


import logging
from django.apps import apps
from utils import get_log_extra_paras

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit_logger')

module_name = __name__
app_name = apps.get_app_config(module_name.split('.')[0]).name
if app_name is None or app_name == "":
    app_name = 'NA'


# Create your views here.
class LoginView(RedirectURLMixin, FormView):
    """
    Display the login form and handle the login action.
    """
    form_class = UserLoginForm
    authentication_form = None
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'registration/login.html'
    redirect_authenticated_user = False
    extra_context = None

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):

        # Redirect already authenticated users to the dashboard
        if request.user.is_authenticated:
            redirect_to = self.get_success_url()
            print("here: redirect_to request.path: ", redirect_to, request.path)
            if redirect_to == request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)

        if request.POST.get('username') is not None and request.POST.get('password') is not None:
            try:

                request_username = request.POST.get('username')

                request_password = request.POST.get('password')

                request_platform = request.POST.get('platform')


                if User.objects.filter(username=request_username).exists():

                    get_password = User.objects.filter(username=request_username).values_list('password',
                                                                                              flat=True).get()
                    matchcheck = check_password(request_password, get_password)

                    if matchcheck:

                        lower_request_platform = request_platform.lower()

                        check_user_role = User.objects.filter(username=request_username).values_list('role',
                                                                                                     flat=True).get()


                        check_last_login = User.objects.filter(username=request_username).values_list('last_login',
                                                                                                      flat=True).get()


                        check_user_platform = User.objects.filter(username=request_username).values_list('platform',
                                                                                                         flat=True).get()

                        lower_database_platform = check_user_platform.lower()


                        if check_user_role == 'aspirant' and lower_request_platform == 'simulation':

                            messages.add_message(request, messages.WARNING, "You are not authorized for simulation")
                            return redirect('/login/')

                        if check_last_login is not None and (check_user_role == 'moderator' or check_user_role == 'admin' or check_user_role == 'observer') and lower_request_platform == 'simulation' and (
                                'simulation' not in lower_database_platform):
                            messages.add_message(request, messages.WARNING, "You are not authorized to access simulation")
                            return redirect('/login/')

                        if check_last_login is not None and (check_user_role == 'moderator' or check_user_role == 'admin' or check_user_role == 'observer') and lower_request_platform == 'training' and (
                                'range' not in lower_database_platform):
                            messages.add_message(request, messages.WARNING, "You are not authorized to access training")
                            return redirect('/login/')

                        if check_last_login is not None and (check_user_role == 'observer' or
                                check_user_role == 'admin' or check_user_role == 'moderator') and lower_request_platform == 'simulation' and (
                                'simulation' in lower_database_platform):
                            request.session['simulation'] = 'admin-simulation'


                        # elif matchcheck and check_last_login is None and (check_user_role == 'observer' or
                        #         check_user_role == 'admin' or check_user_role == 'moderator' ):
                        #     try:
                        #         get_mail = User.objects.filter(email=request.POST.get('username')).values_list('email',
                        #                                                                                        flat=True).get()
                        #     except:
                        #         get_mail = User.objects.filter(username=request.POST.get('username')).values_list(
                        #             'email', flat=True).get()
                        #     return OneTimePasswordChange().post(request, get_mail)

                        
                        # Allow Reset password for all type of users when admin set the default password
                        elif matchcheck and check_user_role in {'observer', 'admin', 'moderator', 'aspirant'}:
                            try:
                                get_mail = User.objects.filter(email=request.POST.get('username')).values_list('email', flat=True).get()
                            except:
                                get_mail = User.objects.filter(username=request.POST.get('username')).values_list('email', flat=True).get()

                            # return OneTimePasswordChange().post(request, get_mail)

                            reset_passwd_flag = False
                            print("here: check_user_role, request_password: ", check_user_role, request_password)
                            # Here, If aspirant user password is 'aspirant', it means admin created(or reseted the password) this user and password reset action should take place,
                            # If it is not aspirant password, it means end user created this user so don't allow reset password
                            if check_user_role == 'aspirant' and request_password and request_password == 'aspirant':
                                reset_passwd_flag = True

                            # Same for moderator as well
                            elif check_user_role == 'moderator' and request_password and request_password == 'moderator':
                                reset_passwd_flag = True

                            # Same for observer as well
                            elif check_user_role == 'observer' and request_password and request_password == 'observer':
                                reset_passwd_flag = True

                            if reset_passwd_flag is True:
                                return OneTimePasswordChange().post(request, get_mail)

                    else:
                        logger_message = f"User logged in failed for User `{request.POST.get('username')}`, Invalid credentials"
                        logger.error(logger_message)
                        audit_logger.error(logger_message, extra=get_log_extra_paras(self.request, app_name))

            except User.DoesNotExist:
                logger_message = f"User logged in failed, User `{request.POST.get('username')}` not found!"
                logger.error(logger_message)
                audit_logger.error(logger_message, extra=get_log_extra_paras(self.request, app_name))
                pass

        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):

        url = self.get_redirect_url()

        logger_message = f"User `{self.request.user.username}({self.request.user.role})` logged in successfully!"
        logger.info(logger_message)
        audit_logger.info(logger_message, extra=get_log_extra_paras(self.request, app_name))

        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )

        return redirect_to if url_is_safe else ''

    def get_form_class(self):
        return self.authentication_form or self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Security check complete. Log the user in."""

        auth_login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update({
            self.redirect_field_name: self.get_redirect_url(),
            'site': current_site,
            'site_name': current_site.name,
            **(self.extra_context or {})
        })
        return context


class OneTimePasswordChange(View):
    def post(self, request, email):
        form = PasswordChangeForm(request.user, request.POST)
        return render(request, 'password_change_one_time.html', {'form': form, 'email': email})

def change_one_time_password(request):
    try:
        if request.method == 'POST':
            user = request.POST.get('email')
            old_password = request.POST.get("old_password")
            new_password = request.POST.get("new_password1")
            new_password_confirm = request.POST.get("new_password2")

            try:
                fetch_user_pwd = User.objects.filter(email=request.POST.get('email')).values_list('password',
                                                                                                  flat=True).get()
                fetch_user_role = User.objects.filter(email=request.POST.get('email')).values_list('role',
                                                                                                   flat=True).get()
                # Allowing aspirant to reset the password, so commenting below lines
                # if fetch_user_role == 'aspirant':
                #     return HttpResponse("Only admin or moderator can change password here")
            
            except User.DoesNotExist:
                return HttpResponse('Invalid')

            if old_password == new_password:
                return HttpResponse("Old password and New password are same. Please choose different password.")

            matchcheck = check_password(old_password, fetch_user_pwd)

            if matchcheck:

                if new_password != new_password_confirm:
                    return HttpResponse("Password confirmation doesn't match New password")
                else:
                    new = make_password(new_password)
                    matchnewpassword = check_password(new_password_confirm, new)
                    if matchnewpassword:
                        if len(new_password_confirm) < 8:
                            return HttpResponse("The password must contain minimum 8 characters")

                            # check for digit
                        if not any(char.isdigit() for char in new_password_confirm):
                            return HttpResponse(('Password must contain at least 1 digit.'))

                            # check for letter
                        if not any(char.isalpha() for char in new_password_confirm):
                            return HttpResponse(('Password must contain at least 1 letter.'))

                        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')


                        if (regex.search(new_password_confirm) == None):
                            return HttpResponse(('Password must contain at least 1 special char.'))

                        u = User.objects.get(email=request.POST.get('email'))
                        u.set_password(new_password_confirm)
                        u.last_login = datetime.now()
                        u.save()

                        logger_message = f"One time password updated successfully for User `{user}`!"
                        logger.info(logger_message)
                        audit_logger.info(logger_message, extra=get_log_extra_paras(request, app_name))

                        return HttpResponse("logout")

                    else:
                        return HttpResponse("Password must be at least 8 characters long and choose strong password.")

            else:
                return HttpResponse("Old Password doesn't match with the database.")
    except Exception as e:
        logger_message = f"Exception occurred while updating the one time password: {str(e)}"
        logger.error(logger_message)
        audit_logger.error(logger_message, extra=get_log_extra_paras(request, app_name))
        print(logger_message)
        return HttpResponse("Error occurred while updating the password.")

def login_success(request):
    if (request.user.role == 'admin' or request.user.role == 'moderator' or request.user.role == 'observer') and 'simulation' in request.session:
        return redirect('canvas')
    elif (request.user.role == 'admin' or request.user.role == 'observer' or request.user.role == 'moderator') and 'simulation' not in request.session:
        return redirect('dashboard')
    else:
        return redirect("/profile/")  # or your url name

def generate_aside_menu(request):
    available_menus = []
    if request.user.role == 'admin' or request.user.role == 'moderator' or request.user.role == 'observer':
        available_menus = [
            {'text':'Home','value':'range_activity','image':'home.png'},
            {'text':'Topology','value':'topology','image':'topology.svg'},
            {'text':'Credentials','value':'credentials','image':'credentials.svg'},
            {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
            {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
            {'text': 'Reporting', 'value': 'reporting', 'image': 'reporting.svg'},
            {'text':'Health Status','value':'health-status','image':'heart.svg'},
        ]

    if request.user.role == 'aspirant':
        if request.user.aspirant_role == 'blue':
            available_menus = [
                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                {'text': 'Topology', 'value': 'topology', 'image': 'topology.svg'},
                {'text': 'Credentials', 'value': 'credentials', 'image': 'credentials.svg'},
                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},

            ]
        elif request.user.aspirant_role == 'red_vs_blue':
            print("**************************", request.user.username)
            # redvsblue_role = CyberGameParticipants.objects.filter(is_running=1).values()
            redvsblue_role = list(CyberGameParticipants.objects.filter(is_running=True).values('participants_rating'))

            # Check if redvsblue_role has participants data
            if redvsblue_role:
                participants_data = redvsblue_role[0].get('participants_rating', [])

                if isinstance(participants_data, list) and participants_data:  # Ensure it's a non-empty list
                    # Find the participant's role by matching the username
                    participant = next((p for p in participants_data if p['name'] == request.user.username), None)

                    if participant:
                        participants_role = participant.get('role', None)  # Get the 'role' of the current user
                        print("participants_role", participants_role)

                        # Define menu based on role
                        if participants_role == 'blue':
                            available_menus = [
                                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                                {'text': 'Topology', 'value': 'topology', 'image': 'topology.svg'},
                                {'text': 'Credentials', 'value': 'credentials', 'image': 'credentials.svg'},
                                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                            ]
                        elif participants_role == 'red':
                            available_menus = [
                                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                            ]
                        else:
                            # Default menu if no role found
                            available_menus = [
                                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                            ]
                    else:
                        # Handle case where the participant is not found
                        available_menus = [
                            {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                            {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                            {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                        ]
                else:
                    # Handle case where participants_rating is empty or unexpected format
                    available_menus = [
                        {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                        {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                        {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                    ]
            else:
                # Handle case where no data is found
                available_menus = [
                    {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                    {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                    {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                ]


        elif request.user.aspirant_role == 'red':
            available_menus = [
                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},

            ]
        elif request.user.aspirant_role == 'ctf':
            available_menus = [
                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
                {'text': 'Leaderboard', 'value': 'leaderboard', 'image': 'goal.svg'},
                {'text': 'CTF', 'value': 'range_activity/ctf', 'image': 'flags.svg'},
            ]
        elif request.user.aspirant_role == 'threez_lab':
            available_menus = [
                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
            
            ]
        else:
            available_menus = [
                {'text': 'Home', 'value': 'profile', 'image': 'home.png'},
                {'text': 'Settings', 'value': 'settings', 'image': 'settings.png'},
            ]

    content = {
        'available_menus' : available_menus,
        'role' : request.user.role
    }

    return JsonResponse(content, safe=False)



def empty_url_redirection(request):
    return redirect('/login/')


# Function to logout the user and clear the session
def logout_user(request):
    print("here: logout_user")
    try:
        # Log the logout event
        logger_message = f"User `{request.user.username}` logged out successfully!"

        # Logout the user
        logout(request)

        logger.info(logger_message)
        audit_logger.info(logger_message, extra=get_log_extra_paras(None, app_name))
        
        # Redirect to the login page
        response = redirect('/login/')
        
        # Set cache control headers to prevent caching
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response['Pragma'] = 'no-cache'  # For older HTTP/1.0 caches
        response['Expires'] = '0'  # Proxies

        return response
    except Exception as e:
        # Log the error and return the error message
        logger_message = f"Exception occurred while logging out the user: {str(e)}"
        logger.error(logger_message)
        audit_logger.error(logger_message, extra=get_log_extra_paras(request, app_name))
        print(logger_message)
        content = {
            'message': "Error Occurred while logging out",
            'status': 'Error'
        }
        return JsonResponse(content, safe=False)

