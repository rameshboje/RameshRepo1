from django.http import HttpResponse, Http404
from django.shortcuts import redirect

def check_simulation_session(view_func):
    def wrapper_func(request, *args, **kwargs):
        if 'simulation' in request.session and request.session[
            'simulation'] == 'admin-simulation' and (request.user.role == 'admin' or request.user.role == 'moderator'):
            return view_func(request, *args, **kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func