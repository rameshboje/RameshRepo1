from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from .models import Credential
from threez_lab.models import TemplateDetails
# from django.conf import settings
import logging
from django.views.decorators.csrf import csrf_exempt
import json
# from notify.models import Notification
# from notify.signals import notify
# from django.db.models import Q
from django.utils import timezone
# from datetime import datetime
from users.authorization import machine_permissions, admin_moderator_only
from django.apps import apps

from settingspage.views import fetch_esxi_cred
from settingspage.models import LabDetails
from vm_scripts.helpers import VmHelper
from vm_scripts.templates import create_template_vm, delete_template_vm

# celery
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from PurpleRange.celeryapp import app

'''
@login_required decorator is used to provide access to the functions only on login 
'''
logger = logging.getLogger(__name__)


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def create_machine_template(request):
    try:
        print("here: create-machine_template: ")
        # get data in request
        request_data = json.loads(request.body)['params']['data']

        template_name = request_data['template_name']
        template_description = request_data['template_description']
        machine_name = request_data['machine_name']

        if request.user.role == 'admin' or request.user.role == 'moderator':

            # Check for valid template_name
            if not template_name or template_name == "NA":
                contents = {
                    'status': "error",
                    'message': "Please provide valid template name!",
                }
                return JsonResponse(contents, safe=False)

            # Check if template already exists TemplateDetails table
            existing_templates = TemplateDetails.objects.filter(template_name=template_name)
            if existing_templates.exists():
                message = f"The template name `{template_name}` already exists. Please enter a unique template name!"
                contents = {'message': message, 'status': 'error'}
                return JsonResponse(contents, safe=False)

            # Fetch existing template details from the database
            existing_template_details = []
            template_details_table_info = {}
            arr_obj_credentials = list(Credential.objects.filter(machine_name=machine_name).values())
            if len(arr_obj_credentials) > 0 and arr_obj_credentials[0]['template_details']:
                existing_template_details = arr_obj_credentials[0]['template_details']['templates_info']
                template_details_table_info["os"] = arr_obj_credentials[0]["os"] if arr_obj_credentials[0]["os"] else "NA"
                template_details_table_info["host"] = arr_obj_credentials[0]["host"] if arr_obj_credentials[0]["host"] else "NA"
                template_details_table_info["username"] = arr_obj_credentials[0]["username"] if arr_obj_credentials[0]["username"] else "NA"
                template_details_table_info["password"] = arr_obj_credentials[0]["password"] if arr_obj_credentials[0]["password"] else "NA"

            MAX_TEMPLATES_PER_MACHINE = 3
            no_of_vm_templates = len(existing_template_details)

            # Check if the number of templates exceeds the maximum allowed
            if no_of_vm_templates >= MAX_TEMPLATES_PER_MACHINE:
                # return failure response
                contents = {
                    'status': "error",
                    'message': "You can create maximum of {} templates. This machine already has {} templates".format(
                        MAX_TEMPLATES_PER_MACHINE, no_of_vm_templates)
                }
                return JsonResponse(contents, safe=False)

            # -----------------Check celery worker status-------------------------------------

            # Celery services are up or not
            i = app.control.inspect()
            celery_status = i.ping()

            if bool(celery_status) is True:
                machine_template_details = {
                    "template_name": template_name,
                    "machine_name": machine_name,
                    "template_description": template_description,
                }

                # Add template to existing templates array
                temp_obj = {
                    "template_name": template_name,
                    "template_description": template_description,
                }
                existing_template_details.append(temp_obj)

                add_template_details = {
                    "templates_info": existing_template_details
                }

                res = create_machine_template_vsphere.delay(machine_template_details, add_template_details, template_details_table_info, username=request.user.username)
                task_id = res.id
                contents = {
                    "message": "Template created successfully!",
                    "status": "success",
                    "task_id": task_id,
                }
                return JsonResponse(contents, safe=False)

            else:
                response_msg = "Critical processes are down. Please try again or contact support."
                return JsonResponse({'status': 'error', 'message': response_msg})

            # --------------------------------------------------------------------------

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
            'message': f'Exception occurred while creating machine template. {str(e)}.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def delete_machine_templates(request):
    try:
        print("here: delete-machine_templates: ")

        if request.user.role == 'admin' or request.user.role == 'moderator':

            # get data in request
            request_data = json.loads(request.body)['params']['data']

            # -----------------Check celery worker status------------------------

            # Celery services are up or not
            i = app.control.inspect()
            celery_status = i.ping()

            if bool(celery_status) is True:

                # Delete templates from database

                arr_deletable_machines_template_details = []
                for item in request_data:
                    machine_name = item["machine_name"]
                    template_name = item["template_name"]
                    print("here: deleted template details: ", item)

                    # Fetch existing template details from the database
                    existing_template_details = []
                    arr_obj_template_details = list(Credential.objects.filter(machine_name=machine_name).values('template_details'))
                    if len(arr_obj_template_details) > 0 and arr_obj_template_details[0]['template_details']:
                        existing_template_details = arr_obj_template_details[0]['template_details']['templates_info']

                    # Filter templates with template_name
                    filtered_template_details = [template for template in existing_template_details if
                                                 template["template_name"] != template_name]

                    temp_del_template_details = {
                        "templates_info": filtered_template_details
                    }

                    temp_obj = {
                        "deleted_machine_name": machine_name,
                        "deleted_template_details": temp_del_template_details,
                    }
                    arr_deletable_machines_template_details.append(temp_obj)

                res = delete_machine_templates_vsphere.delay(request_data, arr_deletable_machines_template_details, username=request.user.username)
                task_id = res.id

                contents = {
                    "message": "Template(s) deleted successfully!",
                    "status": 'success',
                    "task_id": task_id,
                }
                return JsonResponse(contents, safe=False)
            else:
                response_msg = "Critical processes are down. Please try again or contact support."
                return JsonResponse({'status': 'error', 'message': response_msg})
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
            'message': 'Exception occurred while deleting the templates. Please check the log file.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@shared_task(bind=True, name="Create machine template from Credentials page")
def create_machine_template_vsphere(self, machine_template_details, add_template_details, template_details_table_info, **kwargs):

    # for celery progress bar
    progress_recorder = ProgressRecorder(self)

    try:
        print("here: create-machine_template_vsphere: ", machine_template_details, kwargs)

        # init helpers
        vm_helper = VmHelper()

        # login to vsphere
        progress_recorder.set_progress(10, 100, description="Logging into vSphere")
        service_instance = vm_helper.vm_login()

        machine_name = machine_template_details["machine_name"]
        template_name = machine_template_details["template_name"]
        template_description = machine_template_details["template_description"]

        # fetch enabled esxi server details
        progress_recorder.set_progress(20, 100, description="Fetching esxi server details")
        cred_details = fetch_esxi_cred()
        print("here: cred-details: ", cred_details)

        if cred_details['status'] == 'success':
            default_values = cred_details['res']

            # Fetch 3Z lab template folder from LabDetails
            lab_conf = list(LabDetails.objects.filter(enabled='enabled', lab_type="3Z lab").values())
            print("here: lab_conf1: ", lab_conf)
            if len(lab_conf) > 0:
                default_values["template_folder"] = lab_conf[0]["template_folder"]
            else:
                _json = {
                    "status": "error",
                    "message": "Please add Lab Details(3Z lab) under Settings Page"
                }
                return _json

            # If it is cluster, fetch PR Labs folder name
            if default_values["is_cluster"]:
                # Fetch PR Lab folder name from LabDetails
                lab_conf = list(LabDetails.objects.filter(enabled='enabled', lab_type="PR lab").values())
                print("here: lab_conf2: ", lab_conf)
                if len(lab_conf) > 0:
                    default_values["folder"] = lab_conf[0]["vm_folder"]
                else:
                    _json = {
                        "status": "error",
                        "message": "Please add PR Lab Details under Settings Page"
                    }
                    return _json
            else:
                default_values["folder"] = ""

            # Setting template_name and description into default variable
            default_values["template_name"] = template_name
            default_values["description"] = template_description

            progress_recorder.set_progress(30, 100, description="Creating template on vSphere")

            # create template of the machine
            res_create_template = create_template_vm(
                service_instance,
                machine_name,
                default_values
            )
            print("here: res-create_template: ", res_create_template)

            if res_create_template:
                response_msg = res_create_template["res"]
                status = res_create_template["status"]
            else:
                response_msg = "Error occurred while creating template!"
                status = "error"

            # If Template created successfully on vSphere, then only update the template details on database
            if status == "success":
                # Add this template into TemplateDetails table
                create_temp_obj = TemplateDetails.objects.create(
                    template_name=template_name,
                    username=template_details_table_info['username'],
                    password=template_details_table_info['password'],
                    operating_system=template_details_table_info['os'],
                    host_name=template_details_table_info['host'],
                    added_from="credentials"
                )
                create_temp_obj.save()

                Credential.objects.filter(machine_name=machine_name).update(
                    template_details=add_template_details,
                    updated_at=timezone.now()
                )

            logger.info(response_msg)

            print("here: Creating the template from Credentials page task completed!")
            progress_recorder.set_progress(100, 100, description=response_msg)
            res_data = {
                "status": status,
                "message": response_msg,
                "machine_name": machine_name,
                "template_name": template_name,
            }
            return res_data

        else:
            response_msg = "Error while fetching the esxi details, {}.".format(cred_details['res'])
            logger.info(response_msg)
            progress_recorder.set_progress(100, 100, description='Error while fetching the esxi details!')
            res_data = {
                "status": "error",
                "message": response_msg,
                "machine_name": machine_name,
                "template_name": template_name,
            }
            return res_data

    except Exception as e:
        print("here: Exception Occurred: create-machine_template_vsphere: ", str(e))
        response_msg = f'Exception occurred while creating the template: {str(str(e))} !'
        progress_recorder.set_progress(100, 100, description=response_msg)
        res_data = {
            "status": "error",
            "message": response_msg,
            "machine_name": machine_template_details["machine_name"],
            "template_name": machine_template_details["template_name"],
        }
        return res_data


@shared_task(bind=True, name="Delete machine templates from Credentials page")
def delete_machine_templates_vsphere(self, machine_template_details, arr_deletable_machines_template_details, **kwargs):

    # for celery progress bar
    progress_recorder = ProgressRecorder(self)

    try:
        print("here: delete-machine_template_vsphere: ", machine_template_details, arr_deletable_machines_template_details, kwargs)

        # init helpers
        vm_helper = VmHelper()

        # login to vsphere
        service_instance = vm_helper.vm_login()

        # fetch enabled esxi server details
        cred_details = fetch_esxi_cred()
        print("here: cred-details: ", cred_details)

        if cred_details['status'] == 'success':
            default_values = cred_details['res']

            # Fetch 3Z lab template folder from LabDetails
            lab_conf = list(LabDetails.objects.filter(enabled='enabled', lab_type="3Z lab").values())
            print("here: lab_conf1: ", lab_conf)
            if len(lab_conf) > 0:
                default_values["template_folder"] = lab_conf[0]["template_folder"]
            else:
                _json = {
                    "status": "error",
                    "message": "Please add Lab Details(3Z lab) under Settings Page"
                }
                return _json

            # If it is cluster, fetch PR Labs folder name
            if default_values["is_cluster"]:
                # Fetch PR Lab folder name from LabDetails
                lab_conf = list(LabDetails.objects.filter(enabled='enabled', lab_type="PR lab").values())
                print("here: lab_conf2: ", lab_conf)
                if len(lab_conf) > 0:
                    default_values["folder"] = lab_conf[0]["vm_folder"]
                else:
                    _json = {
                        "status": "error",
                        "message": "Please add PR Lab Details under Settings Page"
                    }
                    return _json
            else:
                default_values["folder"] = ""

            total_items = len(machine_template_details)
            complete_perc = 0
            perc = 100 / total_items

            # Iterating through machine_template_details to delete machine template on vsphere
            task_response = []
            for item in machine_template_details:
                machine_name = item["machine_name"]
                template_name = item["template_name"]

                # Setting template_name and description into default variable
                default_values["template_name"] = template_name
                default_values["description"] = "Deleting the template from Credentials page"

                # delete template of the machine
                res_template = delete_template_vm(
                    service_instance,
                    machine_name,
                    default_values
                )
                print("here: res-delete_template: ", res_template)

                if res_template:
                    response_msg = res_template["res"]
                    status = res_template["status"]
                else:
                    response_msg = "Error occurred while deleting the template!"
                    status = "error"

                logger.info(response_msg)

                # If Template deleted successfully on vSphere, then only update the template details on database
                if status == "success":
                    # When template delete from vSphere, Delete record from TemplateDetails table
                    TemplateDetails.objects.filter(template_name=template_name).delete()

                    for del_mach_template_obj in arr_deletable_machines_template_details:
                        if del_mach_template_obj["deleted_machine_name"] == machine_name:
                            Credential.objects.filter(machine_name=machine_name).update(
                                template_details=del_mach_template_obj["deleted_template_details"],
                                updated_at=timezone.now()
                            )
                            break

                # Calculating task progress percentage
                complete_perc = complete_perc + perc

                # Setting task progress
                response_message = f'Deleting the {str(template_name)} template!'
                progress_recorder.set_progress(complete_perc, 100, description=response_message)

                res_data = {
                    "status": status,
                    "message": response_msg,
                    "machine_name": machine_name,
                    "template_name": template_name,
                }
                task_response.append(res_data)

            print("here: Deleting the templates from Credentials page task completed!")
            return task_response

        else:
            response_msg = "Error while fetching the esxi details, {}.".format(cred_details['res'])
            logger.info(response_msg)
            progress_recorder.set_progress(100, 100, description='Error while fetching the esxi details!')
            res_data = {
                "status": "error",
                "message": response_msg,
                "machine_template_details": machine_template_details,
            }
            return [res_data]

    except Exception as e:
        print("here: Exception Occurred: delete-machine_template_vsphere: ", str(e))
        response_msg = 'Exception occurred while deleting the templates from Credentials page!'
        progress_recorder.set_progress(100, 100, description=response_msg)
        res_data = {
            "status": "error",
            "message": response_msg,
            "machine_template_details": machine_template_details,
        }
        return [res_data]
