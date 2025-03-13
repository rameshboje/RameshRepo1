from django.shortcuts import render, redirect
from datetime import datetime
import hashlib
from django.contrib import messages
from django.http import Http404, HttpResponse
import logging
logger = logging.getLogger(__name__)

"""
Middleware checks whether the license for every request/response is valid or not
"""
class CanvasMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        if request.user.is_authenticated and 'simulation' in request.session and request.session['simulation'] == 'admin-simulation':
            split_path = request.path.split("/")
            if split_path[0] == '':
                split_path_result = split_path[1]
            else:
                split_path_result = split_path[0]

            if split_path_result == 'canvas' or split_path_result == 'logout' or split_path_result == 'login' or split_path_result == 'login_success':
                return response
            else:
                raise Http404('Not found')
        else:
            return response







