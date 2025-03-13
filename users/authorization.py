from django.http import HttpResponse, Http404
from django.shortcuts import redirect


def unauthenticated_user(view_func):
    def wrapper_func(request,*args,**kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func


def admin_moderator_only(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.role == 'admin' or request.user.role == 'moderator' or request.user.role == 'observer':
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def admin_only(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.role == 'admin':
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def aspirant_only(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.role == 'aspirant' and (request.user.aspirant_role == 'blue' or request.user.aspirant_role == 'red' or request.user.aspirant_role == 'red_vs_blue'):
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def aspirant_role_blue(view_func):
    def wrapper_func(request,*args,**kwargs):
        if (request.user.aspirant_role == 'blue' or request.user.aspirant_role == 'red_vs_blue') and request.user.role == 'aspirant':
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def aspirant_role_red(view_func):
    def wrapper_func(request,*args,**kwargs):
        if (request.user.aspirant_role == 'red' or request.user.aspirant_role == 'red_vs_blue') and request.user.role == 'aspirant':
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def aspirant_role_ctf(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.aspirant_role == 'ctf' and request.user.role == 'aspirant':
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func


def machine_permissions(view_func):
    def wrapper_func(request,*args,**kwargs):
        if request.user.role == 'admin' or request.user.role == 'moderator'  or request.user.role == 'observer' or  (request.user.role == 'aspirant' and (request.user.aspirant_role == 'blue' or request.user.aspirant_role == 'red_vs_blue')):
            return view_func(request,*args,**kwargs)
        else:
            raise Http404('Not Found')
    return wrapper_func
