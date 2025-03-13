from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
import time
# from .models import UserLabs
from django.utils import timezone
# import request
import base64
# from .models import VMDetails
from .models import Credential
from vm_scripts.helpers import VmHelper, acquire_mks_ticket
from pyVmomi import vim

import logging
from django.apps import apps





@login_required(login_url='/login')
@csrf_exempt
def lanch_vm_console_cred(request):
    try:
        print("here: lanch-vm_console")
        machine_name = request.GET['machine_name']
        machine_name = base64.b64decode(machine_name).decode('utf-8')
        print("here: machine_name: ", machine_name)

        # machine_name = "CRO_cus_emsPriLba_newuser33"
        vsphere_vm_name = ""
        vm_helper = VmHelper()
        service_instance = vm_helper.vm_login()
        
        if isinstance(service_instance, dict) and 'error' in service_instance:
            content = { 'status': -1, 'data': service_instance['error'] }
            return JsonResponse(content, safe=False)

        content = service_instance.RetrieveContent()
        vm_response = vm_helper.get_obj(content, [vim.VirtualMachine], machine_name)
        print("here: vm_response: ", vm_response)
        if vm_response['status'] == "success":
            vsphere_vm_id = str(vm_response['res'])
            print("here: vsphere_vm_id: ", vsphere_vm_id, type(vsphere_vm_id))
            if vsphere_vm_id and ":" in vsphere_vm_id:
                vsphere_vm_name = vsphere_vm_id.split(":")[1]
                vsphere_vm_name = vsphere_vm_name.replace("'", "")
        else:
            
            content = { 'status': -1, 'data': vm_response }
            return JsonResponse(content, safe=False)

        # vsphere_vm_name = "vm-3853"
        print("here: vsphere_vm_name: ", vsphere_vm_name)
        res_data = acquire_mks_ticket(vsphere_vm_name)
        print("here: acquire_mks_ticket: res_data: ", res_data)

        if res_data and len(res_data) > 0 and res_data["status"] == "success":

            str_ticket = ""
            if 'ticket' in res_data['data'] and res_data['data']['ticket'] and res_data['data']['ticket'] is not None:
                str_ticket = res_data['data']['ticket']
                print("here: ticket found!: ", str_ticket)
            else:
                data = f"ticket not found for VM {vm_name}!"
                print("here: ", data)
                
                content = { 'status': -1, 'data': data }
                return JsonResponse(content, safe=False)

            # Code to extract IP address and tickect id from str_ticket-------
            # Split the string by "://" to get the part after "wss:"
            split_parts = str_ticket.split("//")[1]
            ip_address = split_parts.split(":")[0]
            ticket_parts = str_ticket.split("/")
            ticket_id = ticket_parts[-1]
            print("IP Address:", ip_address)
            print("Ticket ID:", ticket_id)
            # --------------------------------------------------------------------------

            data = { "url" :  str_ticket, "ip_address": ip_address, "ticket_id": ticket_id}
            return render(request, 'open_vm_console_cred.html', data)
        else:
            
            content = { 'status': -1, 'data': res_data['data'] }
            return JsonResponse(content, safe=False)

    except Exception as e:
        data = f"Exception occurred while lanch-vm_console: {str(e)}"
        print("here: ", data)
        content = { 'status': -1, 'data': data }
        
        return JsonResponse(content, safe=False)

