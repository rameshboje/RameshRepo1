from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from django_celery_results.models import TaskResult
import time

from .decorator import check_simulation_session
from vm_scripts.machines import Machines
# from vm_scripts.power_on_all import power_on_single_machine
from vm_scripts.helpers import VmHelper
from django.conf import settings
import logging
logger = logging.getLogger(__name__)


@login_required(login_url='/login')
@check_simulation_session
def index(request):
    if 'simulation' in request.session and request.session['simulation'] == 'admin-simulation' and (request.user.role == 'admin' or request.user.role == 'moderator'):
        return render(request, 'canvas.html')
    else:
        raise Http404('Not found')


@login_required(login_url='/login')
@check_simulation_session
def fetch_topology(request):
    try:
        file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
        file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
        file_node = os.path.join(settings.MEDIA_ROOT, 'topology', 'node.json')
        file_link = os.path.join(settings.MEDIA_ROOT, 'topology', 'link.json')
        folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

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
            with open(file_topology, "r", encoding='utf-8') as out:

                if len(out.readlines()) > 0:
                    out.seek(0)
                    json_data = json.loads(out.read())

        if os.path.isfile(folder + 'node.json'):
            with open(file_node, "r", encoding='utf-8') as out:
                out.seek(0)
                nodes = json.loads(out.read())

        if os.path.isfile(folder + 'link.json'):
            with open(file_link, "r", encoding='utf-8') as out:
                out.seek(0)
                links = json.loads(out.read())

        contents = {
            'nodes': nodes,
            'links': links,
            'json_data': json_data,
            'status': 'success'
        }
        return JsonResponse(contents, safe=False)

    except Exception as e:
        logger.info(e)
        contents = {
            'msg' : 'Exception occured. Please check log file',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def validate_before_publish(request):
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')

    if os.path.isfile(folder + 'temp.json'):
        with open(file_json, "r", encoding='utf-8') as out:
            json_data = json.loads(out.read())
            if len(json_data['switches']) > 0 or len(json_data['machines']) > 0 or len(
                    json_data['changes']['switches']) or len(json_data['changes']['machines']):
                contents = {
                    'message': 'success',
                    'status': 200
                }
            else:
                contents = {
                    'message': 'No changes has been detected.',
                    'status': -1
                }
    else:
        contents = {
            'message': 'No changes has been detected.',
            'status': -1
        }

    return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def check_implemented_status(request):
    try:
        folder = os.path.join(settings.MEDIA_ROOT, 'topology/')
        if os.path.isfile(folder + 'topology.json'):
            is_implemented = True
        else:
            is_implemented = False

        content = {
            'status': is_implemented
        }
        return JsonResponse(content, safe=False)
    except Exception as e:
        logger.info(e)
        return HttpResponse('Exception occured.')



"""
@Todo Ask Nishant for duplicate switch check
"""
@login_required(login_url='/login')
@check_simulation_session
def fetch_switch_if_implemented(request):
    switch = request.GET['data']
    type_ = request.GET['type']
    switch = int(switch)

    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')


    if os.path.isfile(folder + 'topology.json'):
        with open(file_topology, "r", encoding='utf-8') as out:
            out.seek(0)
            json_data = json.loads(out.read())
            switch_data = list(filter(lambda x: x['id'] == switch and x['type'] == type_, json_data['switches']))
        if len(switch_data) > 0:
            content = {
                'status': 200
            }
        else:
            content = {
                'status': -1
            }
    else:
        if os.path.isfile(folder + 'temp.json'):
            with open(file_temp, "r", encoding='utf-8') as out:
                out.seek(0)
                json_data = json.loads(out.read())

                switch_data = list(filter(lambda x: x['id'] == switch and x['status'] == 'success' and x['type'] == type_, json_data['switches']))
            if len(switch_data) > 0:
                content = {
                    'status': 200
                }
            else:
                content = {
                    'status': -1
                }
        else:
            content = {
                'status': -1
            }

    return JsonResponse(content, safe=False)

@login_required(login_url='/login')
@check_simulation_session
def fetch_machine_if_implemented(request):
    # print(request)

    machine = request.GET['data']
    type_ = request.GET['type']
    print(machine)
    print(type_)

    machine = int(machine)

    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')

    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')


    if os.path.isfile(folder + 'topology.json'):
        with open(file_topology, "r", encoding='utf-8') as out:
            out.seek(0)
            json_data = json.loads(out.read())

            try:
                machine_data = list(filter(lambda x: x['id'] == machine and x['type'] == type_, json_data['machines']))
            except KeyError as error:
                content = {
                    'status': -1
                }
                return JsonResponse(content, safe=False)

        if len(machine_data) > 0:
            content = {
                'status': 200
            }
        else:
            content = {
                'status': -1
            }
    else:
        if os.path.isfile(folder + 'temp.json'):
            with open(file_temp, "r", encoding='utf-8') as out:
                out.seek(0)
                json_data = json.loads(out.read())
                try:
                    machine_data = list(filter(lambda x: x['id'] == machine and x['status'] == 'success' and x['type'] == type_, json_data['machines']))
                except KeyError as error:
                    content = {
                        'status': -1
                    }
                    return JsonResponse(content, safe=False)

            if len(machine_data) > 0:
                content = {
                    'status': 200
                }
            else:
                content = {
                    'status': -1
                }
        else:
            content = {
                'status': -1
            }

    return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def fetch_machine_to_delete_implemented(request):
    machine = request.GET['data']
    type_ = request.GET['type']
    machine = int(machine)

    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')

    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')


    if os.path.isfile(folder + 'topology.json'):
        with open(file_topology, "r", encoding='utf-8') as out:
            out.seek(0)
            json_data = json.loads(out.read())
            machine_data = list(filter(lambda x: x['id'] == machine  and x['type'] == type_, json_data['machines']))
        if len(machine_data) > 0:
            content = {
                'status': 200
            }
        else:
            content = {
                'status': -1
            }
    else:
        content = {
            'status': -1
        }

    return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def fetch_switch_to_delete_implemented(request):
    machine = request.GET['data']
    type_ = request.GET['type']
    machine = int(machine)

    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')

    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')


    if os.path.isfile(folder + 'topology.json'):
        with open(file_topology, "r", encoding='utf-8') as out:
            out.seek(0)
            json_data = json.loads(out.read())
            machine_data = list(filter(lambda x: x['id'] == machine and x['type'] == type_, json_data['switches']))
        if len(machine_data) > 0:
            content = {
                'status': 200
            }
        else:
            content = {
                'status': -1
            }
    else:
        content = {
            'status': -1
        }

    return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@check_simulation_session
def save_topology(request):
    json_data = json.loads(request.body)['params']['data']
    nodes = json.loads(request.body)['params']['nodes']
    links = json.loads(request.body)['params']['links']
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_node = os.path.join(settings.MEDIA_ROOT, 'topology', 'node.json')
    file_link = os.path.join(settings.MEDIA_ROOT, 'topology', 'link.json')
    json_object_file = json.dumps(json_data, indent=4)
    json_object_node = json.dumps(nodes, indent=4)
    json_object_link = json.dumps(links, indent=4)

    with open(file_json, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_file)

    with open(file_node, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_node)

    with open(file_link, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_link)

    content = {
        'status': 200,
        'message': 'All the changes has been successfully saved.'
    }

    return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@check_simulation_session
def save_implemented_result(request):
    status = json.loads(request.body)['params']['status']
    json_data = json.loads(request.body)['params']['data']
    nodes = json.loads(request.body)['params']['nodes']
    links = json.loads(request.body)['params']['links']

    file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
    file_node = os.path.join(settings.MEDIA_ROOT, 'topology', 'node.json')
    file_link = os.path.join(settings.MEDIA_ROOT, 'topology', 'link.json')
    json_object_file = json.dumps(json_data, indent=4)
    json_object_node = json.dumps(nodes, indent=4)
    json_object_link = json.dumps(links, indent=4)



    if status:
        if len(nodes) == 0:
            folder = os.path.join(settings.MEDIA_ROOT, 'topology/')
            if os.path.isfile(folder + 'temp.json'):
                os.remove(file_temp)
            if os.path.isfile(folder + 'topology.json'):
                os.remove(file_topology)
            if os.path.isfile(folder + 'node.json'):
                os.remove(file_node)
            if os.path.isfile(folder + 'link.json'):
                os.remove(file_link)
        else:
            with open(file_topology, "w", encoding='utf-8') as out:
                out.seek(0)
                out.write(json_object_file)
                os.remove(file_temp)
    else:
        with open(file_topology, "w", encoding='utf-8') as out:
            out.seek(0)
            out.write(json_object_file)

        with open(file_temp, "w", encoding='utf-8') as out:
            out.seek(0)
            out.write(json_object_file)

    with open(file_node, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_node)

    with open(file_link, "w", encoding='utf-8') as out:
        out.seek(0)
        out.write(json_object_link)

    content = {
        'message': 'The saved simulation data updated successfully.',
        'status': 200
    }

    return JsonResponse(content, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@check_simulation_session
def get_task_result(request):
    # print(request.GET['data'])
    id =  request.GET['data']
    # id =  "d9622331-d96a-4678-8879-a276eaa20b1d"

    time.sleep(3)
    fetch_result_progress = list(TaskResult.objects.filter(task_id=id, status='PROGRESS').values('result','status'))
    fetch_result_success = list(TaskResult.objects.filter(task_id=id, status='SUCCESS').values('result','status'))
    fetch_result_failure = list(TaskResult.objects.filter(task_id=id, status='FAILURE').values('result','status'))




    if len(fetch_result_success) > 0:
        json_object_file = fetch_result_success[0]['result']
        contents = {
            'json_data': json.loads(json_object_file),
            'status': fetch_result_success[0]['status']
        }
    elif len(fetch_result_progress) > 0:
        json_object_file = fetch_result_progress[0]['result']
        contents = {
            'json_data':  json.loads(json_object_file),
            'status': fetch_result_progress[0]['status']
        }
    elif len(fetch_result_failure) > 0:
        json_object_file = fetch_result_failure[0]['result']
        contents = {
            'json_data':  json.loads(json_object_file),
            'status': fetch_result_failure[0]['status']
        }
    else:
        contents = {
            'json_data': 'Error while fetching.',
            'status': -1
        }

    return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def create_topology(request):
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'result.json')

    with open(file_json, "r", encoding='utf-8') as out:
        json_data = json.loads(out.read())

    contents = {
        'json_data': json_data,
        'status': 'SUCCESS'
    }
    return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@check_simulation_session
def open_console_in_browser(request):

    try:
        vm_name = request.GET['data']
        data_center = settings.VS_DC
        host = settings.VS_HOST
        host_domain = settings.VS_HOST_DOMAIN
        # resource_pool = settings.VS_RP_Simulation VS_RP_Simulation
        resource_pool = 'Simulation'
        vcenter_ip = settings.VS_IP
        machine_helper = Machines()
        vm_helper = VmHelper()

        # login to vsphere
        service_instance = vm_helper.vm_login()
        url = machine_helper.open_browser_console(service_instance, vm_name, data_center, host, host_domain, resource_pool, vcenter_ip)

        final_url = {"url": url, "status": "success"}

        return JsonResponse(final_url)

    except Exception as e:
        # logger.info(e)
        return HttpResponse(e)




