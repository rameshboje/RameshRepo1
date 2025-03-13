from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from django.core import serializers
from django_celery_results.models import TaskResult
from django.db.models import Q

'''
@login_required decorator is used to provide access to the functions only on login 
'''


def index(request):
    if request.user.role == 'admin' or request.user.role == 'moderator':
        return render(request, 'canvas.html')
    else:
        raise Http404('Not found')


@login_required
@csrf_exempt
def fetch_topology(request):
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_node = os.path.join(settings.MEDIA_ROOT, 'topology', 'node.json')
    file_link = os.path.join(settings.MEDIA_ROOT, 'topology', 'link.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')

    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

    is_implemented = False
    nodes = []
    links = []
    json_data = {
        'switches': [],
        'machines': [],
        'changes': {
            'switches': [],
            'machines': [],
        }
    }

    if os.path.isfile(folder + 'temp.json'):
        with open(file_json, "r", encoding='utf-8') as out:
            if len(out.readlines()) > 0:
                out.seek(0)
                json_data = json.loads(out.read())
    elif os.path.isfile(folder + 'topology.json'):
        is_implemented = True
        with open(file_topology, "r", encoding='utf-8') as out:

            if len(out.readlines()) > 0:
                out.seek(0)
                json_data = json.loads(out.read())

    if os.path.isfile(folder + 'topology.json'):
        is_implemented = True

    if os.path.isfile(folder + 'node.json'):
        with open(file_node, "r", encoding='utf-8') as out:
            out.seek(0)
            nodes = json.loads(out.read())

    if os.path.isfile(folder + 'link.json'):
        with open(file_link, "r", encoding='utf-8') as out:
            out.seek(0)
            links = json.loads(out.read())

    contents = {
        'isImplemented': is_implemented,
        'nodes': nodes,
        'links': links,
        'json_data': json_data
    }
    return JsonResponse(contents, safe=False)


@login_required
@csrf_exempt
def save_topology(request):
    json_data = json.loads(request.body)['params']['data']
    nodes = json.loads(request.body)['params']['nodes']
    links = json.loads(request.body)['params']['links']

    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_node = os.path.join(settings.MEDIA_ROOT, 'topology', 'node.json')
    file_link = os.path.join(settings.MEDIA_ROOT, 'topology', 'link.json')
    json_object_file = json.dumps(json_data, indent=4)
    json_object_node = json.dumps(nodes, indent=4)
    json_object_link = json.dumps(links, indent=4)
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

    # if os.path.isfile(folder + 'topology.json'):
    #     if len(json_data['changes']['switches']) == 0 and len(json_data['changes']['machines']) == 0:
    #         with open(file_topology, "w", encoding='utf-8') as out:
    #             out.seek(0)
    #             out.write(json_object_file)
    #     else:
    with open(file_json, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_file)
    # else:
    #     with open(file_json, "w", encoding='utf-8') as out:
    #         out.seek(0)
    #         out.write(json_object_node)

    with open(file_node, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_node)

    with open(file_link, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_link)


    return HttpResponse('ok')


@login_required
@csrf_exempt
def implement_topology(request):
    json_data = json.loads(request.body)['params']['data']

    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')

    json_object_file = json.dumps(json_data, indent=4)

    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')


    if os.path.isfile(folder + 'temp.json'):
        with open(file_temp, "r", encoding='utf-8') as out:
            out.seek(0)
            temp_json = out.read()
            content = {
                'json': temp_json
            }


    return HttpResponse('ok')

@login_required
@csrf_exempt
def processor(request):
    return HttpResponse('ok')


def fetch_saved_topology(request):
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

    contents = {
        'message':'Please create a machines to publish.',
        'status':-1
    }

    if os.path.isfile(folder + 'temp.json'):
        with open(file_json, "r", encoding='utf-8') as out:
            if len(out.readlines()) > 0:
                out.seek(0)
                json_data = json.loads(out.read())
                contents = {
                    'message': json_data,
                    'status':200
                }

    return JsonResponse(contents, safe=False)



@login_required
@csrf_exempt
def save_topology_publish(request):

    status = json.loads(request.body)['params']['status']
    json_data = json.loads(request.body)['params']['data']


    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')
    json_object_file = json.dumps(json_data, indent=4)


    if status == 'no error':
        with open(file_topology, "w", encoding='utf-8') as out:
            out.seek(0)
            out.write(json_object_file)
            os.remove(file_temp)
    else:
        with open(file_temp, "w", encoding='utf-8') as out:
            out.seek(0)
            out.write(json_object_file)

    content = {
        'message': 'Process Completed.'
    }

    return JsonResponse(content,safe=False)


@login_required
@csrf_exempt
def fetch_implemented_result(request):
    # file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'result.json')
    # folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

    id = json.loads(request.body)['params']['data']
    fetch_result = list(TaskResult.objects.filter(task_id=id,status='PROGRESS').values('result')[0:1])
    json_object_file = fetch_result[0]

    if len(fetch_result) > 0:
        contents = {
            'message': json_object_file,
            'status': 200
        }
        return JsonResponse(contents, safe=False)

    else:
        contents = {
            'message': 'Please wait while the process in running.',
            'status': -1
        }
        return JsonResponse(contents, safe=False)


@login_required
@csrf_exempt
def fetch_canvas_notification(request):
    try:
        notifications = list(TaskResult.objects.filter(Q(task_name__icontains='Simulation lab progress'), Q(result__icontains='error') | Q(result__icontains='not found') |
                               Q(result__icontains='exception')).values('task_kwargs','result','status','date_created')[:10])
        content = {
            'result' :  notifications,
            'status' : 'success'
        }
        return JsonResponse(content, safe=False)
    except Exception as e:
        content = {
            'result': e,
            'status': 'success'
        }
        return JsonResponse(content, safe=False)







