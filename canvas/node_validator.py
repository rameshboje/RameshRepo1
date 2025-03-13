from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import socket
import re
from ipaddress import ip_network, ip_address
from .decorator import check_simulation_session




@login_required
@csrf_exempt
@check_simulation_session
def check_switch_ip_subnet_is_valid(request):

    switch_data = json.loads(request.body)['params']['data']
    split_data = switch_data.split("/")

    if len(split_data) == 2:
        ip = split_data[0]
        subnet = split_data[1]
        regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                    25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                    25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                    25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

        if (re.search(regex, ip)):
            if int(subnet) > 0 and int(subnet) <= 24:
                content = {
                    'status': 200,
                    'message': 'Subnet added successfully.'
                }
            else:
                content = {
                    'status': -1,
                    'message': 'Subnet should be less than 24'
                }
        else:
            content = {
                'status': -1,
                'message': 'IP is not valid'
            }


    else:
        content = {
            'status': -1,
            'message': 'IP should followed by subnet'
        }

    return JsonResponse(content, safe=False)


@login_required
@csrf_exempt
@check_simulation_session
def check_machine_is_valid(request):

    machine_data = json.loads(request.body)['params']['data']
    name = machine_data['name']
    nic = machine_data['nic']
    os = machine_data['guest_id']
    regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                       25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                       25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                       25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''



    if name:
        if os:
            if len(nic) > 0 and len(nic) <= 30:
                for n in nic:
                    print("--------------------")
                    print(n)
                    print("--------------------------")

                    if n['switch']:
                        if n['ip'] and re.search(regex, n['ip']):
                            switch_data = n['switch'].split("_")[1]

                            net = ip_network(switch_data)

                            print(">>>>>>>>>>>>>>>>>>>>>>")
                            print(n['ip'])
                            print(switch_data)
                            print(net)
                            print(ip_address(n['ip']) in net)
                            print(">>>>>>>>>>>>>>>>>>>>>>")

                            if ip_address(n['ip']) in net:
                                if re.search(regex, n['gateway']) or n['gateway'] == "":
                                    content = {
                                        'status': 200,
                                        'message': 'Endpoint added successfully.'
                                    }
                                else:
                                    content = {
                                        'status': -1,
                                        'message': 'Invalid Gateway given for {}'.format(n['name'])
                                    }
                                    break

                            else:
                                content = {
                                    'status': -1,
                                    'message': 'IP address not falling under the given subnet for {}'.format(n['name'])
                                }
                                break
                            # return JsonResponse(content, safe=False)
                        else:
                            content = {
                                'status': -1,
                                'message': 'Invalid IP given for {}'.format(n['name'])
                            }
                            break
                            # return JsonResponse(content, safe=False)

                    else:
                        content = {
                            'status': -1,
                            'message': 'Please provide the switch for {}'.format(n['name'])
                        }
                        break
                    # return JsonResponse(content, safe=False)
            else:
                content = {
                    'status': -1,
                    'message': 'Min 1 or Max 30 nics are allowed.'
                }

        else:
            content = {
                'status': -1,
                'message': 'Please select OS.'
            }

    else:
        content = {
            'status': -1,
            'message': 'NIC should not be empty.'
        }


    return JsonResponse(content, safe=False)
    # print(json.loads(request.body))
    #
    # switch_data = json.loads(request.body)['params']['data']
    # split_data = switch_data.split("/")
    #
    # if len(split_data) == 2:
    #     ip = split_data[0]
    #     subnet = split_data[1]
    #     regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
    #                 25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
    #                 25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
    #                 25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''
    #
    #     if (re.search(regex, ip)):
    #         if int(subnet) > 0 and int(subnet) <= 24:
    #             content = {
    #                 'status': 200,
    #                 'message': 'Subnet added successfully.'
    #             }
    #         else:
    #             content = {
    #                 'status': -1,
    #                 'message': 'Subnet should be less than 24'
    #             }
    #     else:
    #         content = {
    #             'status': -1,
    #             'message': 'IP is not valid'
    #         }
    #
    #
    # else:
    #     content = {
    #         'status': -1,
    #         'message': 'IP should followed by subnet'
    #     }
    #
    # return JsonResponse(content, safe=False)
#
# @login_required
# @csrf_exempt
# def check_machine_is_valid(request):
#
#     machine_data = json.loads(request.body)['params']['data']
#     print(machine_data)
#     name = machine_data['name']
#     nic = machine_data['nic']
#     os = machine_data['guest_id']
#     regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
#                        25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
#                        25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
#                        25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''
#
#     if name:
#         file_topology = os.path.join(settings.MEDIA_ROOT, 'topology', 'topology.json')
#         file_temp = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
#
#         folder = os.path.join(settings.MEDIA_ROOT, 'topology/')
#
#         if os.path.isfile(folder + 'topology.json'):
#             with open(file_topology, "r", encoding='utf-8') as out:
#                 out.seek(0)
#                 json_data = json.loads(out.read())
#                 machine_data = list(
#                     filter(lambda x: x['machine_name'] == name, json_data['machines']))
#                 if len(machine_data) > 0:
#                     content = {
#                         'status': -1,
#                         'message': 'Name already exist. Provide Unique Name'
#                     }
#                     return JsonResponse(content, safe=False)
#         if os.path.isfile(folder + 'temp.json'):
#             with open(file_temp, "r", encoding='utf-8') as out:
#                 out.seek(0)
#                 json_data = json.loads(out.read())
#                 machine_data = list(
#                     filter(lambda x: x['machine_name'] == name, json_data['machines']))
#                 if len(machine_data) > 0:
#                     content = {
#                         'status': -1,
#                         'message': 'Name already exist. Provide Unique Name'
#                     }
#                     return JsonResponse(content, safe=False)
#
#                 if json_data['changes']:
#                     machine_data = list(
#                         filter(lambda x: x['machine_name'] == name, json_data['changes']['machines']))
#                     if len(machine_data) > 0:
#                         content = {
#                             'status': -1,
#                             'message': 'Name already exist. Provide Unique Name'
#                         }
#                         return JsonResponse(content, safe=False)
#
#         if os:
#             if len(nic) > 0 and len(nic) <= 16:
#                 print(range(len(nic)))
#                 for n in range(len(nic)):
#
#                     if nic[n]['switch']:
#                         if nic[n]['ip'] and re.search(regex, nic[n]['ip']):
#                             switch_data = nic[n]['switch'].split("_")[1]
#
#                             net = ip_network(switch_data)
#                             if ip_address(nic[n]['ip']) in net:
#                                 if re.search(regex, nic[n]['gateway']) or nic[n]['gateway'] == "":
#                                     content = {
#                                         'status': 200,
#                                         'message': 'Endpoint added successfully.'
#                                     }
#                                     # return JsonResponse(content, safe=False)
#                                 else:
#                                     content = {
#                                         'status': -1,
#                                         'message': 'Invalid Gateway given for {}'.format(nic[n]['name'])
#                                     }
#                                     # return JsonResponse(content, safe=False)
#
#                             else:
#                                 content = {
#                                     'status': -1,
#                                     'message': 'IP address not falling under the given subnet for {}'.format(nic[n]['name'])
#                                 }
#                                 # return JsonResponse(content, safe=False)
#                         else:
#                             content = {
#                                 'status': -1,
#                                 'message': 'Invalid IP given for {}'.format(nic[n]['name'])
#                             }
#                             # return JsonResponse(content, safe=False)
#                     else:
#                         content = {
#                             'status': -1,
#                             'message': 'Please provide the switch for {}'.format(nic[n]['name'])
#                         }
#                         # return JsonResponse(content, safe=False)
#             else:
#                 content = {
#                     'status': -1,
#                     'message': 'Min 1 or Max 16 nics are allowed.'
#                 }
#                 # return JsonResponse(content, safe=False)
#         else:
#             content = {
#                 'status': -1,
#                 'message': 'Please select OS.'
#             }
#             # return JsonResponse(content, safe=False)
#     else:
#         content = {
#             'status': -1,
#             'message': 'Name should not be empty.'
#         }
#
#     return JsonResponse(content, safe=False)