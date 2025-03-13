from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from django_celery_results.models import TaskResult
from .models import VMGuestId
from .models import VirtualSwitches
from .models import MachineTemplates
from .models import VMGuestId
from .decorator import check_simulation_session
import logging
logger = logging.getLogger(__name__)

@login_required(login_url='/login')
@check_simulation_session
def fetch_guestid(request):
    try:
        guest = list(VMGuestId.objects.values_list('name', flat=True))
        content = {
            'guest': guest,
            'status': 'success'
        }
        return JsonResponse(content, safe=False)
    except Exception as e:
        logger.info(e)
        content = {
            'msg' : 'Exception occured while retrieving guest os. Please check log file',
            'status': 'error'
        }
        return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def fetch_switches(request):
    try:
        switch = list(VirtualSwitches.objects.values('switch_name', 'port_group_name'))
        for d in switch:
            d.update({'text': d['port_group_name']})
            d['value'] = d.pop('port_group_name')

        content = {
            'switch': switch,
            'status': 'success'
        }
        return JsonResponse(content, safe=False)
    except Exception as e:
        logger.info(e)
        content = {
            'msg' : 'Exception occured while retrieving swicthes. Please check log file',
            'status': 'error'
        }
        return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def fetch_templates(request):
    try:
        template = list(MachineTemplates.objects.values('template_name'))
        for d in template:
            d.update({'text': d['template_name']})
            d['value'] = d.pop('template_name')
            d['is_available'] = 0

        content = {
            'template': template,
            'status': 'success'
        }
        return JsonResponse(content, safe=False)
    except Exception as e:
        logger.info(e)
        content = {
            'msg': 'Exception occured while retrieving templates. Please check log file',
            'status': 'error'
        }
        return JsonResponse(content, safe=False)

