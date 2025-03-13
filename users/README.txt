1. views.py

    2 class based functions
    4 view functions


    a. LoginView - class based function

        used to validate credentials , platform access and authenticates an user either to training platform or simulation platform

    b. OneTimePasswordChange - class based function

        used to render `first time password change` html page to the user.

    c. change_one_time_password - view function

        used to change the password of moderator for the first time login to the portal.

    d. generate_aside_menu - view function

        used to generate navigation menu for aside bar based on role

    e. empty_url_redirection - view function

        If only IP is typed in the browser, this function will redirect to /login/
        Ex: http://1.1.1.1

................................................

2. authorization.py - decorator

    a. unauthenticated_user - not used yet
        used to redirect to login if user is not authenticated

    b. admin_moderator_only
       additional layer to check role is admin/moderator

    c. admin_only
       additional layer to check role is admin

    d. aspirant_only
       additional layer to check role is aspirant

...........................................

3. models.py - User auth_table

...............................

4. forms.py - User login form fields
