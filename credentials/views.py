from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.core import serializers
from .models import Credential
from .forms import CredentialForm, EditCredentialForm
import os
from django.conf import settings
import logging
from django.views.decorators.csrf import csrf_exempt
import json
from users.models import User
from notify.models import Notification
from notify.signals import notify
import socket
from django.db.models import Q
from django.utils import timezone
from django.core.files.storage import default_storage
import re
from datetime import datetime
from settingspage.models import VsphereDetails, HostDetails
from users.authorization import machine_permissions, admin_moderator_only
from django.apps import apps

'''
@login_required decorator is used to provide access to the functions only on login 
'''
logger = logging.getLogger(__name__)


# Create your views here.
@login_required(login_url='/login')
@machine_permissions
def index(request):
    return render(request, 'credentials.html')


'''
Used to download credentials in pdf format - used in version 1
'''


# @login_required(login_url='/login')
# def download_pdf(request):
#     try:
#         filename = "credentials.pdf"
#
#         # fetch file name from the media/credentials dir
#         file_path = os.path.join(settings.MEDIA_ROOT, 'credentials/' + filename)
#
#         # check file exists
#         if os.path.exists(file_path):
#             # open binary file in read mode
#             with open(file_path, 'rb') as fh:
#                 # serve file as pdf
#                 response = HttpResponse(fh.read(), content_type="application/pdf")
#                 # on click attach/download a file
#                 response['Content-Disposition'] = "attachment; filename=" + filename
#                 return response
#         raise Http404
#     except:
#         logger.info("Whatever the exceptions goes here")


@login_required(login_url='/login')
@machine_permissions
@csrf_exempt
def credentials_machines_table(request):
    try:
        # To fetch the logged in user role
        fetch_user_role = User.objects.filter(username=request.user.username).values_list('role', flat=True).get()
        # if user role is admin
        if fetch_user_role == "admin":
            # fetch the credential page information from the credential tables
            total_credential = list(Credential.objects.values())

            # Headers for Admin
            headers = [
                {
                    'text': 'Machine Name',
                    'align': 'start',
                    'sortable': False,
                    'value': 'machine_name',
                },
                {'text': 'Machine SnapShot', 'value': 'snap_shot_name'},
                {'text': 'IP Address', 'value': 'ip', 'sortable': True},
                {'text': 'Username', 'value': 'username', 'sortable': True},
                {'text': 'Password', 'value': 'password', 'sortable': True},
                {'text': 'RDP IP', 'value': 'rdp_ip', 'sortable': True},
                {'text': 'Connect Via', 'value': 'connect_via', 'sortable': False},
                {'text': 'Action', 'value': 'actions', 'sortable': False, 'width': '150px'},
            ]

            contents = {

                'total_credential': total_credential,
                'headers': headers,
            }
            return JsonResponse(contents, safe=False)
        else:
            # fetch the credential page information from the credential tables
            total_credential = list(
                Credential.objects.filter(machine_type='Visible').values("ip", "username", "password", "machine_name",
                                                                         'connect_via', 'snap_shot_name',
                                                                         'machine_used', 'rdp_ip', 'os',
                                                                         'conn_name', 'host_conn_name', 'host',
                                                                         'server_ip',
                                                                         'data_store', 'data_center', 'resource_pool',
                                                                         'host_domain', 'updated_at','red_vs_blue_type','is_red_vs_blue'))

            headers = [
                {
                    'text': 'Machine Name',
                    'align': 'start',
                    'sortable': False,
                    'value': 'machine_name',
                },

                {'text': 'IP Address', 'value': 'ip', 'sortable': True},
                {'text': 'Username', 'value': 'username', 'sortable': True},
                {'text': 'Password', 'value': 'password', 'sortable': True},
                {'text': 'RDP IP', 'value': 'rdp_ip', 'sortable': True},
                {'text': 'Connect Via', 'value': 'connect_via', 'sortable': True},
                {'text': 'Updated At', 'value': 'updated_at', 'sortable': True},
                {'text': 'Action', 'value': 'actions', 'sortable': False},

            ]

            contents = {

                'total_credential': total_credential,
                'headers': headers,
            }
            return JsonResponse(contents, safe=False)

    except Exception as e:
        print("here: Exception Occurred: ", e)
        logger.info(e)
        return HttpResponse("Exception occured. Check log file.")


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def edit_credential(request):
    try:
        # get data in request
        # response = json.loads(request.body)['params']['data']
        # print("****************************************************************")

        response = {
            'machine_name': request.POST['machine_name'],
            'machine_type': request.POST['machine_type'],
            'username': request.POST['username'],
            'password': request.POST['password'],
            'ip': request.POST['ip'],
            'rdp_ip': request.POST['rdp_ip'],
            'description': request.POST['description'],
            'connect_via': request.POST['connect_via'],
            'os': request.POST['os'],
            'conn_name': request.POST['conn_name'],
            'host_conn_name': request.POST['host_conn_name'],
            'machine_used': request.POST['machine_used'],
            'is_reverted': request.POST['is_reverted'],
            'is_red_vs_blue': True if request.POST['is_red_vs_blue'].lower() == 'true' else False,
            'red_vs_blue_type':request.POST['red_vs_blue_type']
        }
        print("here: request data : ", response)

        # To check Ip and machine name is exists or not
        if Credential.objects.filter(~Q(machine_name=response['machine_name']), ip=response['ip']).exists():
            contents = {
                "message": "Ip already exist for different machine",
                "status": 'error',
            }
            return JsonResponse(contents, safe=False)
        else:
            pass

        if request.POST['rdp_ip']:
            obj_credentails = Credential.objects.filter(~Q(machine_name=response['machine_name']), rdp_ip=request.POST['rdp_ip'])
            if obj_credentails.exists():
                contents = {
                    "message": f"The RDP IP address `{request.POST['rdp_ip']}` is already in use. Please provide a unique RDP IP address.",
                    "status": 'error',
                }
                return JsonResponse(contents, safe=False)

        if HostDetails.objects.filter(conn_name=response['conn_name'],
                                      host_conn_name=response['host_conn_name']).exists():
            host_details = HostDetails.objects.filter(host_conn_name=response['host_conn_name']).values(
                'host', 'server_ip', 'data_store', 'data_center', 'resource_pool', 'host_domain', 'username', 'password'
            )
            host = host_details[0]['host']
            server_ip = host_details[0]['server_ip']
            data_store = host_details[0]['data_store']
            data_center = host_details[0]['data_center']
            resource_pool = host_details[0]['resource_pool']
            host_domain = host_details[0]['host_domain']
            exsi_username = host_details[0]['username']
            exsi_password = host_details[0]['password']
        else:
            host = 'NA'
            server_ip = 'NA'
            data_store = 'NA'
            data_center = 'NA'
            resource_pool = 'NA'
            host_domain = 'NA'
            exsi_username = 'NA'
            exsi_password = 'NA'

        # Call credentialForm class and pass variables to the function
        form = EditCredentialForm(response)
        # print(form)

        # if form is valid send success message to the front end
        if request.user.role == 'admin':
            if form.is_valid():

                file = request.FILES.get('cred_edit_rdp_file')
                current_datetime = timezone.now()
                # Convert to Unix timestamp (long value)
                timestamp = int(current_datetime.timestamp())
                str_timestamp = str(timestamp)
                file_name = response['rdp_ip'] + "_" + str_timestamp + ".rdp"
                rdp_file_upload_resp = upload_rdp_file(file, file_name)
                if rdp_file_upload_resp['status'] == 'success':
                    rdp_file_name = file_name
                else:
                    rdp_file_name = "NA"

                # ====It means no new file uploaded or invalid file uploaded then set existing/old file name========
                if rdp_file_name == "NA" or rdp_file_name is None or rdp_file_name == "":
                    rdp_file_name = request.POST['rdp_file_name']

                rdp_file_name = rdp_file_name if rdp_file_name else "NA"

                # Credential.objects.filter(machine_name=response['machine_name']).update(**response)
                Credential.objects.filter(machine_name=response['machine_name']).update(
                    ip=response['ip'],
                    username=response['username'],
                    password=response['password'],
                    machine_type=response['machine_type'],
                    description=response['description'],
                    machine_used=response['machine_used'],
                    is_reverted=response['is_reverted'],
                    connect_via=response['connect_via'],
                    rdp_ip=response['rdp_ip'],
                    os=response['os'],
                    conn_name=response['conn_name'],
                    host_conn_name=response['host_conn_name'],
                    host=host,
                    server_ip=server_ip,
                    data_store=data_store,
                    data_center=data_center,
                    resource_pool=resource_pool,
                    host_domain=host_domain,
                    exsi_username=exsi_username,
                    exsi_password=exsi_password,
                    rdp_file_name=rdp_file_name,
                    is_red_vs_blue=response['is_red_vs_blue'],
                    red_vs_blue_type=response['red_vs_blue_type'],
                )

                # ===============Delete old file after updation========
                if request.POST['rdp_file_name_ori'] and rdp_file_name != request.POST['rdp_file_name_ori'] and \
                        request.POST['rdp_file_name_ori'] is not None and request.POST['rdp_file_name_ori'] != "NA":
                    file_path = default_storage.delete(f"credentials/rdp_files/{request.POST['rdp_file_name_ori']}")

                message = 'The machine has been updated successfully.'
                status = 'success'
                contents = {
                    'message': message,
                    'status': status,
                }

            # in case form fields include some error, sends error the the frontend
            elif form.errors:
                form_errors = form.errors.get_json_data(escape_html=True)
                errors = []
                for key in form_errors.keys():
                    errors.append("{k} : {v}".format(k=key, v=form_errors[key][0]['message']))
                message = errors,
                status = 'error'
                contents = {
                    'message': message,
                    'status': status
                }
            else:
                message = 'Exception occurred while updating the credential. Please check log file',
                status = 'error'
                contents = {
                    'message': message,
                    'status': status,
                }

            return JsonResponse(contents, safe=False)
        else:
            contents = {
                "Message": "You are not authorized to perform this task. Please login as admin.",
                "status": 'error',
            }

            return JsonResponse(contents, safe=False)

    except Exception as e:
        logger.info(e)

        print("here: Exception Occurred: ", e)
        contents = {
            'message': 'Exception occurred while updating the credential information. Please check the log file.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def delete_credential(request):
    try:
        # get data in request
        machine_name = json.loads(request.body)['params']['data']
        # To fetch the logged in username
        role = User.objects.filter(username=request.user.username).values_list('role', flat=True).get()
        # if the role is admin
        if role == "admin":
            # to check machine name is exists or not
            if Credential.objects.filter(machine_name=machine_name).exists():

                deleted_rdp_file_name = \
                    Credential.objects.filter(machine_name=machine_name).values('rdp_file_name').first()[
                        'rdp_file_name']
                # To delete the entries
                Credential.objects.filter(machine_name=machine_name).delete()

                if deleted_rdp_file_name and deleted_rdp_file_name is not None and deleted_rdp_file_name != "NA":
                    file_path = default_storage.delete(f"credentials/rdp_files/{deleted_rdp_file_name}")

                contents = {
                    'message': 'Successfully deleted',
                    'status': 200
                }
            else:
                contents = {
                    'message': 'Machine not present',
                    'status': -1
                }

            return JsonResponse(contents, safe=False)
        else:
            contents = {
                'message': 'You are not authorized to perform this task. Please login as admin',
                'status': -1
            }

            return JsonResponse(contents, safe=False)
    except Exception as e:
        logger.info(e)

        return HttpResponse("Exception occured. Check log file")


def upload_rdp_file(file=None, file_name=None):
    print("here upload rdp file")

    if file is not None:
        filesize = file.size
        filename = file.name
        file_extension = filename.split(".")[-1]
        megabyte_limit = 100.0

        if filesize > 0:
            if filename.endswith('.rdp') or filename.endswith('.RDP'):
                if filesize > megabyte_limit * 1024 * 1024:
                    message = "Max file size is %sMB" % str(megabyte_limit),
                    status = 'error'
                    contents = {
                        'message': message,
                        'status': status
                    }
                    return contents

                if len(filename) > 50:
                    message = "File name must be less than 50 chars",
                    status = 'error'

                    contents = {
                        'message': message,
                        'status': status
                    }
                    return contents

                file_path = default_storage.save(f"credentials/rdp_files/{file_name}", file)
                message = "File Uploaded Successfully!",
                status = 'success'
                contents = {
                    'message': message,
                    'status': status,
                }
                return contents

            else:
                message = "Invalid file.",
                status = 'error'

                contents = {
                    'message': message,
                    'status': status
                }
                return contents
        else:
            message = "File cannot be empty.",
            status = 'error'

            contents = {
                'message': message,
                'status': status
            }
            return contents
    else:
        message = "File not found!",
        status = 'erroe'

        contents = {
            'message': message,
            'status': status,
        }
        return contents


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def add_credential(request):
    try:
        # get data in request
        # response = json.loads(request.body)['params']['data']

        if request.POST['rdp_ip']:
            obj_credentails = Credential.objects.filter(rdp_ip=request.POST['rdp_ip'])
            if obj_credentails.exists():
                contents = {
                    "message": f"The RDP IP address `{request.POST['rdp_ip']}` is already in use. Please provide a unique RDP IP address.",
                    "status": 'error',
                }
                return JsonResponse(contents, safe=False)

        response = {
            'username': request.POST['username'],
            'password': request.POST['password'],
            'ip': request.POST['ip'],
            'rdp_ip': request.POST['rdp_ip'],
            'machine_name': request.POST['machine_name'],
            'machine_used': request.POST['machine_used'],
            'machine_type': request.POST['machine_type'],
            'connect_via': request.POST['connect_via'],
            'os': request.POST['os'],
            'description': request.POST['description'],
            'conn_name': request.POST['conn_name'],
            'host_conn_name': request.POST['host_conn_name'],
            'is_reverted': request.POST['is_reverted'],
            'is_red_vs_blue': True if request.POST['is_red_vs_blue'].lower() == 'true' else False,
            'red_vs_blue_type':request.POST['red_vs_blue_type'],
        }
        print("here: request data: ", response['is_red_vs_blue'])
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

        response['snap_shot_name'] = response['machine_name'] + '_SS'

        if HostDetails.objects.filter(conn_name=response['conn_name'],
                                      host_conn_name=response['host_conn_name']).exists():
            host_details = HostDetails.objects.filter(host_conn_name=response['host_conn_name']).values(
                'host', 'server_ip', 'data_store', 'data_center', 'resource_pool', 'host_domain', 'username',
                'password')

            host = host_details[0]['host']
            server_ip = host_details[0]['server_ip']
            data_store = host_details[0]['data_store']
            data_center = host_details[0]['data_center']
            resource_pool = host_details[0]['resource_pool']
            host_domain = host_details[0]['host_domain']
            exsi_username = host_details[0]['username']
            exsi_password = host_details[0]['password']
        else:
            host = 'NA'
            server_ip = 'NA'
            data_store = 'NA'
            data_center = 'NA'
            resource_pool = 'NA'
            host_domain = 'NA'
            exsi_username = 'NA'
            exsi_password = 'NA'

        # Call ProfileForm class and pass variables to the function
        form = CredentialForm(response)

        # if form is valid send success message to the front end
        if request.user.role == 'admin':
            message = ""
            status = ""
            if form.is_valid():
                file = request.FILES.get('cred_rdp_file')
                current_datetime = timezone.now()
                # Convert to Unix timestamp (long value)
                timestamp = int(current_datetime.timestamp())
                str_timestamp = str(timestamp)
                file_name = response['rdp_ip'] + "_" + str_timestamp + ".rdp"
                rdp_file_upload_resp = upload_rdp_file(file, file_name)
                if rdp_file_upload_resp['status'] == 'success':
                    rdp_file_name = file_name
                else:
                    rdp_file_name = "NA"

                create_row = Credential.objects.create(
                    ip=response['ip'],
                    username=response['username'],
                    password=response['password'],
                    machine_type=response['machine_type'],
                    description=response['description'],
                    snap_shot_name=response['snap_shot_name'],
                    machine_name=response['machine_name'],
                    machine_used=response['machine_used'],
                    is_reverted=response['is_reverted'],
                    connect_via=response['connect_via'],
                    rdp_ip=response['rdp_ip'],
                    os=response['os'], conn_name=response['conn_name'],
                    host_conn_name=response['host_conn_name'],
                    host=host, server_ip=server_ip,
                    data_store=data_store, data_center=data_center,
                    resource_pool=resource_pool, host_domain=host_domain,
                    exsi_username=exsi_username, exsi_password=exsi_password,
                    rdp_file_name=rdp_file_name,
                    red_vs_blue_type=response['red_vs_blue_type'],
                    is_red_vs_blue=response['is_red_vs_blue'],

                )

                create_row.save()

                # form.save()
                message = 'The machine has been added successfully.'
                status = 'success'
                contents = {
                    'message': message,
                    'status': status,
                }

            # in case form fields include some error, sends error the the frontend
            if form.errors:
                form_errors = form.errors.get_json_data(escape_html=True)
                errors = []
                for key in form_errors.keys():
                    errors.append("{k} : {v}".format(k=key, v=form_errors[key][0]['message']))
                message = errors,
                status = 'error'

            contents = {
                'message': message,
                'status': status
            }

            return JsonResponse(contents, safe=False)
        else:
            contents = {
                "message": "You are not authorized to perform this task. Please login as admin.",
                "status": 'error',
            }

            return JsonResponse(contents, safe=False)

    except Exception as e:
        logger.info(e)
        print("here: Exception Occurred: ", e)

        contents = {
            'message': 'Exception occurred while adding machine. Please check the log file.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
def fetch_exsi_credentials(request):
    try:
        exsi_servers = list(VsphereDetails.objects.filter(enabled='enabled').values_list('conn_name', flat=True))
        host_servers = list(HostDetails.objects.values_list('host_conn_name', flat=True))
        contents = {
            'exsi_servers': exsi_servers,
            'host_servers': host_servers,
        }

        return JsonResponse(contents, safe=False)
    except Exception as e:
        logger.info(e)
        return HttpResponse(400)
