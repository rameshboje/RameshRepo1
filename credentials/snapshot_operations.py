from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from .models import Credential
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
from vm_scripts.helpers import VmHelper
from vm_scripts.take_snapshot import take_snapshot_vm, delete_snapshot_vm, revert_snapshot_vm
from settingspage.models import LabDetails

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
def take_machine_snapshot(request):
    try:
        print("here: take-machine_snapshot: ")
        # get data in request
        request_data = json.loads(request.body)['params']['data']

        snapshot_name = request_data['snapshot_name']
        snapshot_description = request_data['snapshot_description']
        machine_name = request_data['machine_name']

        if request.user.role == 'admin' or request.user.role == 'moderator':

            # Check for valid snapshot_name
            if not snapshot_name or snapshot_name == "NA":
                contents = {
                    'status': "error",
                    'message': "Please provide valid snapshot name!",
                }
                return JsonResponse(contents, safe=False)

            # Fetch existing snapshot details from the database
            existing_snapshot_details = []
            existing_reverted_snapshot_name = ""
            arr_obj_snapshot_details = list(Credential.objects.filter(machine_name=machine_name).values('snapshot_details'))
            if len(arr_obj_snapshot_details) > 0 and arr_obj_snapshot_details[0]['snapshot_details']:
                existing_snapshot_details = arr_obj_snapshot_details[0]['snapshot_details']['snapshots_info']
                existing_reverted_snapshot_name = arr_obj_snapshot_details[0]['snapshot_details']['reverted_snapshot_name']

            # Filter snapshots with name, there should not be duplicate name for snapshots
            filtered_duplicate_snapshots = [snapshot for snapshot in existing_snapshot_details if
                                            snapshot["snapshot_name"] == snapshot_name]

            if len(filtered_duplicate_snapshots) > 0:
                # return failure response
                contents = {
                    'status': "error",
                    'message': f"The snapshot with name `{snapshot_name}` is already present for this machine, Please use unique name of the snapshot for this machine!"
                }
                return JsonResponse(contents, safe=False)

            MAX_SNAPSHOTS_PER_MACHINE = 3
            no_of_vm_snapshots = len(existing_snapshot_details)

            # Check if the number of snapshots exceeds the maximum allowed
            if no_of_vm_snapshots >= MAX_SNAPSHOTS_PER_MACHINE:
                # return failure response
                contents = {
                    'status': "error",
                    'message': "You can take maximum of {} snapshots. This machine already has {} snapshots".format(
                        MAX_SNAPSHOTS_PER_MACHINE, no_of_vm_snapshots)
                }
                return JsonResponse(contents, safe=False)

            # -----------------Check celery worker status-------------------------------------

            # Celery services are up or not
            i = app.control.inspect()
            celery_status = i.ping()

            if bool(celery_status) is True:
                machine_snapshot_details = {
                    "snapshot_name": snapshot_name,
                    "machine_name": machine_name,
                    "snapshot_description": snapshot_description,
                }

                # Add snapshot to existing snapshots array
                temp_obj = {
                    "snapshot_name": snapshot_name,
                    "snapshot_description": snapshot_description,
                }
                existing_snapshot_details.append(temp_obj)

                add_snapshot_details = {
                    "reverted_snapshot_name": existing_reverted_snapshot_name,
                    "snapshots_info": existing_snapshot_details
                }

                res = take_machine_snapshot_vsphere.delay(machine_snapshot_details, add_snapshot_details, username=request.user.username)
                task_id = res.id
                contents = {
                    "message": "Snapshot taken successfully!",
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
            'message': f'Exception occurred while taking machine snapshot. {str(e)}.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def delete_machine_snapshots(request):
    try:
        print("here: delete-machine-snapshots: ")

        if request.user.role == 'admin' or request.user.role == 'moderator':

            # get data in request
            request_data = json.loads(request.body)['params']['data']

            # -----------------Check celery worker status------------------------

            # Celery services are up or not
            i = app.control.inspect()
            celery_status = i.ping()

            if bool(celery_status) is True:

                # Delete snapshots from database

                arr_deletable_machines_snap_details = []
                for item in request_data:
                    machine_name = item["machine_name"]
                    snapshot_name = item["snapshot_name"]
                    print("here: deleted snapshot details: ", item)

                    # Fetch existing snapshot details from the database
                    existing_snapshot_details = []
                    existing_reverted_snapshot_name = ""
                    arr_obj_snapshot_details = list(Credential.objects.filter(machine_name=machine_name).values('snapshot_details'))
                    if len(arr_obj_snapshot_details) > 0 and arr_obj_snapshot_details[0]['snapshot_details']:
                        existing_snapshot_details = arr_obj_snapshot_details[0]['snapshot_details']['snapshots_info']
                        existing_reverted_snapshot_name = arr_obj_snapshot_details[0]['snapshot_details'][
                            'reverted_snapshot_name']

                    # Filter snapshots with snapshot_name
                    filtered_snapshot_details = [snapshot for snapshot in existing_snapshot_details if
                                                 snapshot["snapshot_name"] != snapshot_name]

                    temp_del_snapshot_details = {
                        "reverted_snapshot_name": existing_reverted_snapshot_name,
                        "snapshots_info": filtered_snapshot_details
                    }

                    temp_obj = {
                        "deleted_machine_name": machine_name,
                        "deleted_snap_details": temp_del_snapshot_details,
                    }
                    arr_deletable_machines_snap_details.append(temp_obj)

                res = delete_machine_snapshots_vsphere.delay(request_data, arr_deletable_machines_snap_details, username=request.user.username)
                task_id = res.id

                contents = {
                    "message": "Snapshot(s) deleted successfully!",
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
        print("here: Exception Occurred: ", str(e))
        contents = {
            'message': f'Exception occurred while deleting the snapshots: {str(e)}',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@login_required(login_url='/login')
@csrf_exempt
@admin_moderator_only
def revert_machine_snapshot(request):
    try:
        print("here: revert-machine_snapshot: ")
        # get data in request
        request_data = json.loads(request.body)['params']['data']

        snapshot_name = request_data['snapshot_name']
        snapshot_description = f"Reverting a `{snapshot_name}` snapshot from Credentials Page"
        machine_name = request_data['machine_name']

        if request.user.role == 'admin' or request.user.role == 'moderator':

            # Fetch existing snapshot details from the database
            existing_snapshot_details = []
            current_reverted_snapshot_name = snapshot_name
            arr_obj_snapshot_details = list(Credential.objects.filter(machine_name=machine_name).values('snapshot_details'))
            if len(arr_obj_snapshot_details) > 0 and arr_obj_snapshot_details[0]['snapshot_details']:
                existing_snapshot_details = arr_obj_snapshot_details[0]['snapshot_details']['snapshots_info']

            # -----------------Check celery worker status-------------------------------------

            # Celery services are up or not
            i = app.control.inspect()
            celery_status = i.ping()

            if bool(celery_status) is True:
                machine_snapshot_details = {
                    "snapshot_name": snapshot_name,
                    "machine_name": machine_name,
                    "snapshot_description": snapshot_description,
                }

                # Setting current reverted_snapshot_name needed for database
                revert_snapshot_details = {
                    "reverted_snapshot_name": current_reverted_snapshot_name,
                    "snapshots_info": existing_snapshot_details
                }

                res = revert_machine_snapshot_vsphere.delay(machine_snapshot_details, revert_snapshot_details, username=request.user.username)
                task_id = res.id
                contents = {
                    "message": "Snapshot reverted successfully!",
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
            'message': f'Exception occurred while reverting machine snapshot. {str(e)}.',
            'status': 'error'
        }
        return JsonResponse(contents, safe=False)


@shared_task(bind=True, name="Take machine snapshot from Credentials page")
def take_machine_snapshot_vsphere(self, machine_snapshot_details, add_snapshot_details, **kwargs):

    # for celery progress bar
    progress_recorder = ProgressRecorder(self)

    try:
        print("here: take-machine_snapshot_vsphere: ", machine_snapshot_details, kwargs)

        # init helpers
        vm_helper = VmHelper()

        # login to vsphere
        progress_recorder.set_progress(10, 100, description="Logging into vSphere")
        service_instance = vm_helper.vm_login()

        machine_name = machine_snapshot_details["machine_name"]
        snapshot_name = machine_snapshot_details["snapshot_name"]
        snapshot_description = machine_snapshot_details["snapshot_description"]

        # fetch enabled esxi server details
        progress_recorder.set_progress(20, 100, description="Fetching esxi server details")
        cred_details = fetch_esxi_cred()
        print("here: cred-details: ", cred_details)

        if cred_details['status'] == 'success':
            default_values = cred_details['res']

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
                        "message": "Please add Lab Details under Settings Page"
                    }
                    return _json
            else:
                default_values["folder"] = ""

            # Setting snapshot_name and description into default variable
            default_values["snapshot_name"] = snapshot_name
            default_values["description"] = snapshot_description

            # Set power_off_vm to `YES` to power off VM after successfully completion of create snapshot
            default_values["power_off_vm_on_success"] = "NO"

            # when use_vm_memory is True: Captures the full state of the VM and ensures data consistency.
            # when use_vm_memory is False: Fast snapshot creation with no memory or application-level consistency.
            default_values["use_vm_memory"] = True

            progress_recorder.set_progress(30, 100, description="Creating snapshot on vSphere")

            # take snapshot of the machine
            res_take_snapshot = take_snapshot_vm(
                service_instance,
                machine_name,
                default_values
            )
            print("here: res-take_snapshot: ", res_take_snapshot)

            if res_take_snapshot:
                response_msg = res_take_snapshot["res"]
                status = res_take_snapshot["status"]
            else:
                response_msg = "Error occurred while taking snapshot!"
                status = "error"

            # If Snapshot created successfully on vSphere, then only update the snapshot details on database
            if status == "success":
                Credential.objects.filter(machine_name=machine_name).update(
                    snapshot_details=add_snapshot_details,
                    updated_at=timezone.now()
                )

            logger.info(response_msg)

            print("here: Taking the snapshot from Credentials page task completed!")
            progress_recorder.set_progress(100, 100, description=response_msg)
            res_data = {
                "status": status,
                "message": response_msg,
                "machine_name": machine_name,
                "snapshot_name": snapshot_name,
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
                "snapshot_name": snapshot_name,
            }
            return res_data

    except Exception as e:
        print("here: Exception Occurred: take-machine_snapshot_vsphere: ", str(e))
        response_msg = f'Exception occurred while taking the snapshot from Credentials page: {str(e)}'
        progress_recorder.set_progress(100, 100, description=response_msg)
        res_data = {
            "status": "error",
            "message": response_msg,
            "machine_name": machine_snapshot_details["machine_name"],
            "snapshot_name": machine_snapshot_details["snapshot_name"],
        }
        return res_data


@shared_task(bind=True, name="Delete machine snapshots from Credentials page")
def delete_machine_snapshots_vsphere(self, machine_snapshot_details, arr_deletable_machines_snap_details, **kwargs):

    # for celery progress bar
    progress_recorder = ProgressRecorder(self)

    try:
        print("here: delete-machine_snapshot_vsphere: ", machine_snapshot_details, arr_deletable_machines_snap_details, kwargs)

        # init helpers
        vm_helper = VmHelper()

        # login to vsphere
        service_instance = vm_helper.vm_login()

        # fetch enabled esxi server details
        cred_details = fetch_esxi_cred()
        print("here: cred-details: ", cred_details)

        if cred_details['status'] == 'success':
            default_values = cred_details['res']

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
                        "message": "Please add Lab Details under Settings Page"
                    }
                    return _json
            else:
                default_values["folder"] = ""

            total_items = len(machine_snapshot_details)
            complete_perc = 0
            perc = 100 / total_items

            # Iterating through machine_snapshot_details to delete machine snapshot on vsphere
            task_response = []
            for item in machine_snapshot_details:
                machine_name = item["machine_name"]
                snapshot_name = item["snapshot_name"]

                # Setting snapshot_name and description into default variable
                default_values["snapshot_name"] = snapshot_name
                default_values["description"] = "Deleting the snapshot from Credentials page"

                # delete snapshot of the machine
                res_snapshot = delete_snapshot_vm(
                    service_instance,
                    machine_name,
                    default_values
                )
                print("here: res-delete_snapshot: ", res_snapshot)

                if res_snapshot:
                    response_msg = res_snapshot["res"]
                    status = res_snapshot["status"]
                else:
                    response_msg = "Error occurred while deleting the snapshot!"
                    status = "error"

                logger.info(response_msg)

                # If Snapshot deleted successfully on vSphere, then only update the snapshot details on database
                if status == "success":
                    for del_mach_snap_obj in arr_deletable_machines_snap_details:
                        if del_mach_snap_obj["deleted_machine_name"] == machine_name:

                            # If Delatable snapshot is reverted snapshot, then reset the reverted_snapshot_name
                            if del_mach_snap_obj.get("deleted_snap_details", {}).get("reverted_snapshot_name") == snapshot_name:
                                del_mach_snap_obj["deleted_snap_details"]["reverted_snapshot_name"] = ""

                            Credential.objects.filter(machine_name=machine_name).update(
                                snapshot_details=del_mach_snap_obj["deleted_snap_details"],
                                updated_at=timezone.now()
                            )
                            break

                # Calculating task progress percentage
                complete_perc = complete_perc + perc

                # Setting task progress
                response_message = f'Deleting the {str(snapshot_name)} snapshot!'
                progress_recorder.set_progress(complete_perc, 100, description=response_message)

                res_data = {
                    "status": status,
                    "message": response_msg,
                    "machine_name": machine_name,
                    "snapshot_name": snapshot_name,
                }
                task_response.append(res_data)

            print("here: Deleting the snapshots from Credentials page task completed!")
            return task_response

        else:
            response_msg = "Error while fetching the esxi details, {}.".format(cred_details['res'])
            logger.info(response_msg)
            progress_recorder.set_progress(100, 100, description='Error while fetching the esxi details!')
            res_data = {
                "status": "error",
                "message": response_msg,
                "machine_snapshot_details": machine_snapshot_details,
            }
            return [res_data]

    except Exception as e:
        print("here: Exception Occurred: delete-machine_snapshot_vsphere: ", str(e))
        response_msg = f'Exception occurred while deleting the snapshots from Credentials page: {str(e)}'
        progress_recorder.set_progress(100, 100, description=response_msg)
        res_data = {
            "status": "error",
            "message": response_msg,
            "machine_snapshot_details": machine_snapshot_details,
        }
        return [res_data]


@shared_task(bind=True, name="Revert machine snapshot from Credentials page")
def revert_machine_snapshot_vsphere(self, machine_snapshot_details, revert_snapshot_details, **kwargs):

    # for celery progress bar
    progress_recorder = ProgressRecorder(self)

    try:
        print("here: revert-machine_snapshot_vsphere: ", machine_snapshot_details, kwargs)

        # init helpers
        vm_helper = VmHelper()

        # login to vsphere
        progress_recorder.set_progress(10, 100, description="Logging into vSphere")
        service_instance = vm_helper.vm_login()

        machine_name = machine_snapshot_details["machine_name"]
        snapshot_name = machine_snapshot_details["snapshot_name"]
        snapshot_description = machine_snapshot_details["snapshot_description"]

        # fetch enabled esxi server details
        progress_recorder.set_progress(20, 100, description="Fetching esxi server details")
        cred_details = fetch_esxi_cred()
        print("here: cred-details: ", cred_details)

        if cred_details['status'] == 'success':
            default_values = cred_details['res']

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
                        "message": "Please add Lab Details under Settings Page"
                    }
                    return _json
            else:
                default_values["folder"] = ""

            # Setting snapshot_name and description into default variable
            default_values["snapshot_name"] = snapshot_name
            default_values["description"] = snapshot_description

            progress_recorder.set_progress(30, 100, description="Reverting snapshot on vSphere")

            # take snapshot of the machine
            res_snapshot = revert_snapshot_vm(
                service_instance,
                machine_name,
                default_values
            )
            print("here: res-take_snapshot: ", res_snapshot)

            if res_snapshot:
                response_msg = res_snapshot["res"]
                status = res_snapshot["status"]
            else:
                response_msg = "Error occurred while reverting the snapshot!"
                status = "error"

            # If Snapshot reverted successfully on vSphere, then only update the snapshot details on database
            if status == "success":
                Credential.objects.filter(machine_name=machine_name).update(
                    snapshot_details=revert_snapshot_details,
                    updated_at=timezone.now()
                )

            logger.info(response_msg)

            print("here: Reverting the snapshot from Credentials page task completed!")
            progress_recorder.set_progress(100, 100, description=response_msg)
            res_data = {
                "status": status,
                "message": response_msg,
                "machine_name": machine_name,
                "snapshot_name": snapshot_name,
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
                "snapshot_name": snapshot_name,
            }
            return res_data

    except Exception as e:
        print("here: Exception Occurred: revert-machine_snapshot_vsphere: ", str(e))
        response_msg = f'Exception occurred while reverting the snapshot from Credentials page: , {str(e)}'
        progress_recorder.set_progress(100, 100, description=response_msg)
        res_data = {
            "status": "error",
            "message": response_msg,
            "machine_name": machine_snapshot_details["machine_name"],
            "snapshot_name": machine_snapshot_details["snapshot_name"],
        }
        return res_data
