from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from .decorator import check_simulation_session
from users.models import User
from django_celery_results.models import TaskResult
from django.views.decorators.csrf import csrf_exempt
from users.authorization import admin_only
import json
from django.db.models import Q
import logging
logger = logging.getLogger(__name__)

'''
@login_required decorator is used to provide access to the functions only on login 
'''


@login_required(login_url='/login')
@check_simulation_session
def canvas_progress(request):
    if 'simulation' in request.session and request.session['simulation'] == 'admin-simulation' and (request.user.role == 'admin' or request.user.role == 'moderator'):
        return render(request, 'canvas_bg_process.html')
    else:
        raise Http404('Not found')


@login_required(login_url='/login')
@check_simulation_session
def get_all_progress(request):
    try:

        fetch_user_role = User.objects.filter(username=request.user.username).values_list('platform', flat=True).get()

        role_list = fetch_user_role.split(",")
        progress = list()
        headers = list()

        if 'simulation' in role_list:
            progress = list( TaskResult.objects.filter(task_name__contains='Simulation lab progress').values())
            headers = [
                {
                    'text': 'Task Name',
                    'align': 'start',
                    'sortable': False,
                    'value': 'task_name',
                },
                {
                    'text': 'User',
                    'value': 'task_kwargs',
                    'align': 'start'
                },

                {'text': 'Task Start Time', 'value': 'date_created', 'align': 'start'},

                {'text': 'Status', 'value': 'status', 'align': 'start'},
                {'text': 'Progress', 'value': 'result', 'align': 'start'},

            ]
            contents = {
                'progress': progress,
                'headers': headers,
                'role': request.user.role,
                'status': 'success'
            }

        else:
            contents = {
                'progress': progress,
                'headers': headers,
                'role': request.user.role,
                'status': 'success'
            }

        return JsonResponse(contents, safe=False)
    except Exception as e:
        logger.info(e)
        contents = {
            'msg': 'Exception occured: ' + str(e),
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@admin_only
def delete_progress(request):
    try:

        selected_id = json.loads(request.body)['params']['data']
        role = User.objects.filter(username=request.user.username).values_list('role', flat=True).get()

        if role == 'admin':
            if len(selected_id) == 1:
                if TaskResult.objects.filter(id=selected_id[0]).exists():
                    delete_task = TaskResult.objects.filter(id=selected_id[0]).delete()

                    contents = {
                        'message': ['Successfully deleted the task'],
                        'status': 200
                    }
                else:
                    contents = {
                        'message': ['Select At least one task to delete'],
                        'status': -1
                    }

                return JsonResponse(contents, safe=False)

            else:
                more_selected_id = Q(id=selected_id[0])

                for task in selected_id[1:]:
                    more_selected_id |= Q(id=task)

                if TaskResult.objects.filter(more_selected_id).exists():
                    TaskResult.objects.filter(more_selected_id).delete()

                    contents = {
                        'message': ['Successfully deleted the task'],
                        'status': 200
                    }
                else:
                    contents = {
                        'message': ['Select At least one task to delete'],
                        'status': -1
                    }

                return JsonResponse(contents, safe=False)

        else:
            contents = {
                'message': ['Not Authorized'],
                'status': -1
            }
            return JsonResponse(contents, safe=False)

    except Exception as e:
        logger.info(e)
        contents = {
            'message': ["Exception occured: " + str(e)],
            'status': -1
        }
        return JsonResponse(contents, safe=False)




