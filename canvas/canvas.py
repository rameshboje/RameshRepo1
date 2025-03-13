# VM
from vm_scripts.helpers import VmHelper
from vm_scripts.machines import Machines
from vm_scripts.networks import Networks, Switches
from vm_scripts.add_disk import AddDisk
# celery
from celery import shared_task
from celery_progress.backend import ProgressRecorder
# models
from canvas.models import VirtualSwitches as SwitchModel
from canvas.models import CustomMachines as MachineModel
# django
from django.http import HttpResponse, JsonResponse
from django.conf import settings
# tests
import json
import sys
import os
from PurpleRange.celeryapp import app

"""
Topology creation/modification
feed json input (from canvas page)

TODO - add IP change support for machines
TODO - fetch default values from DB inside get_default_values_from_db()

Author- Info

__copyright__ = "Copyright @ QOS Technology Pvt. Ltd."
__version__ = "beta"
__maintainer__ = "Ekta"
__email__ = "ekta@qostechnology.in"
__status__ = "development"
"""

# logs
_log_files = {
    'error': settings.MEDIA_ROOT + '/topology/canvas.log',
}


@shared_task(bind=True, name="Simulation lab progress")
def topology(self, inputs=None,**kwargs):
    """
    custom machines:
        create (specify RAM, CPU)
        add CD ROM
        add HDD
        add NIC
        change IP (future)

    clone from template:
        edit first NIC, add remaining
        change IP (future)

    Edit machines:
        rename VM
        modify RAM
        modify CPU
        add/remove NIC
        change IP

    Switches:
        create switch
        delete switch

    :param self:
    :param inputs:
    :return: JSON input
    """

    if inputs is None:
        return "No input (JSON) specified!"

    # init helpers
    vm_helper = VmHelper()
    machine_helper = Machines()
    network_helper = Networks()
    switch_helper = Switches()
    disk_helper = AddDisk()
    progress_recorder = ProgressRecorder(self)

    try:
        # get total number of items (switches and machines)
        total_no_items = len(inputs['switches']) + len(inputs['machines'])

        # account for database actions for switches
        if len(inputs['switches']) > 0:
            total_no_items += 1

        # account for database actions for machines
        if len(inputs['machines']) > 0:
            total_no_items += 1

        response_message = 'Processing Topology '
        progress_recorder.set_progress(0, 100, description=response_message)

        # login to vsphere
        service_instance = vm_helper.vm_login()

        # handle login failure
        if isinstance(service_instance, dict):
            # temp
            print('login failed: ' + service_instance['error'])
            progress_recorder.stop_task(0, 100, exc='Login Failed!')
            return 'Exception occurred while trying to Login.' + service_instance['error']

        # temp
        print('logged in')
        progress_recorder.set_progress(5, 100, description='Logged into Vsphere')

        # get defaults from DB
        default_values = get_default_values_from_db()
        host_name = default_values['esxi_host']
        num_ports = default_values['switch_ports']
        datacenter_name = default_values['data_center']
        resource_pool_name = default_values['resource_pool']

        # init lists for DB
        switchtes_to_add = []
        switches_to_delete = []
        failed_switches = []
        new_machines = []
        deleted_machines = []
        edited_machines = []
        failed_machines = []

        # counter variable
        item_counter = 0

        # --------------------------------------------------------------- switches
        for switches in inputs['switches']:
            # (switches can only be deleted, not modified)

            # increment counter for each iteration
            item_counter += 1

            # calculate percentage
            current_switch_index = inputs['switches'].index(switches)
            percent = (current_switch_index + 1) / total_no_items * 100
            try:
                # fetch switch data from DB
                switch_data = SwitchModel.objects.get(switch_id=switches['switch_id']).__dict__

                """
                If switches are found in DB:
                    for delete action - delete the switch
                    for new switch - fail with error
                if not:
                    for delete action - fail with error
                    for new switch - create new switch                                  
                """

                if switches['activity'] == 'new':
                    # temp
                    progress_recorder.set_progress(percent, 100, description='Switch {} already exists!'.format(
                        switches['switch_name']))

                    # add to list
                    failed_switches.insert(len(failed_switches), switches['switch_name'])

                    # update JSON
                    inputs['switches'][current_switch_index]['status'] = 'failed'
                    inputs['switches'][current_switch_index]['activity'] = 'implement'
                    inputs['switches'][current_switch_index]['message'] = 'Switch {} already exists !'.format(switches['switch_name'])

                if switches['activity'] == 'delete':
                    # temp
                    response_message += 'Deleting switch {} '.format(switch_data['switch_name'])
                    progress_recorder.set_progress(percent, 100, description='Deleting switch {} <br>'.format(switch_data['switch_name']))

                    delete_switch = switch_helper.main(
                        'delete',
                        service_instance,
                        host_name,
                        switch_data['switch_name']
                    )

                    # if successful
                    if delete_switch['status'] == "success":
                        print('Deleted switch {}'.format(switch_data['switch_name']))
                        progress_recorder.set_progress(percent, 100, description='Deleting switch {}: Done!'.format(
                            switch_data['switch_name']))

                        # add to list
                        switches_to_delete.insert(len(switches_to_delete), switches['switch_id'])

                        # update JSON
                        inputs['switches'][current_switch_index]['status'] = 'success'
                        inputs['switches'][current_switch_index]['activity'] = 'deleted'
                    else:
                        # temp
                        progress_recorder.set_progress(percent, 100, description='Deleting switch {}: Failed!'.
                                                       format(switch_data['switch_name']))
                        # add to list
                        failed_switches.insert(len(failed_switches), switches['switch_id'])

                        # update JSON
                        inputs['switches'][current_switch_index]['status'] = 'failed'
                        inputs['switches'][current_switch_index]['activity'] = 'deleted'
                        inputs['switches'][current_switch_index]['message'] = delete_switch['res']

            # if no switch was found in DB, for this ID
            except SwitchModel.DoesNotExist:
                print("Dont exist")

                if switches['activity'] == 'new':
                    # temp
                    print("-----------------------------------")
                    print(switches['switch_name'])
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print(switches)
                    response_message += 'Creating switch {} '.format(switches['switch_name'])
                    progress_recorder.set_progress(percent, 100, description='Creating switch {} <br>'.
                                                   format(switches['switch_name']))

                    create_switch = switch_helper.main(
                        'create',
                        service_instance,
                        host_name,
                        switches['switch_name'],
                        num_ports,
                        switches['port_group']
                    )
                    print("Hello all, i am here.")
                    print(create_switch)
                    # if successful
                    if create_switch['status'] == "success":
                        # temp
                        print('Switch Created {}'.format(switches['switch_name']))
                        print(percent)
                        progress_recorder.set_progress(percent, 100, description='Creating switch: Done!')

                        # add to list
                        db_insert = {
                            "switch_name": switches['switch_name'],
                            "switch_id": switches['switch_id'],
                            "port_group_name": switches['port_group'],
                            "subnet": switches['subnet']
                        }
                        switchtes_to_add.insert(len(switchtes_to_add), db_insert)

                        # update JSON
                        inputs['switches'][current_switch_index]['status'] = 'success'
                        inputs['switches'][current_switch_index]['activity'] = 'implement'
                    else:
                        # if switch creation fails for any  reason, attempt to delete it
                        # delete_switch = switch_helper.main(
                        #     'delete',
                        #     service_instance,
                        #     host_name,
                        #     switches['switch_name']
                        # )
                        # print('Deleting switch: {}'.format(delete_switch))

                        # temp
                        progress_recorder.set_progress(percent, 100, description='Creating switch {}: Failed!'.format(
                            switches['switch_name']))

                        # add to list
                        failed_switches.insert(len(failed_switches), switches['switch_name'])

                        # update JSON
                        inputs['switches'][current_switch_index]['status'] = 'failed'
                        inputs['switches'][current_switch_index]['activity'] = 'implement'
                        inputs['switches'][current_switch_index]['message'] = create_switch['res']

                if switches['activity'] == 'delete':
                    # temp
                    progress_recorder.set_progress(percent, 100, description='Creating switch {}: Failed!'.
                                                   format(switches['switch_id']))

                    # add to list
                    failed_switches.insert(len(failed_switches), switches['switch_id'])

                    # update JSON
                    inputs['switches'][current_switch_index]['status'] = 'failed'
                    inputs['switches'][current_switch_index]['activity'] = 'implement'
                    inputs['switches'][current_switch_index]['message'] = 'Switch {} Not found in DB'.format(switches['switch_id'])

        # update DB
        if len(inputs['switches']) > 0:
            # increment counter for each iteration
            item_counter += 1
            # percent
            percent = item_counter / total_no_items * 100
            progress_recorder.set_progress(percent, 100, description='Writing changes to DB')

            # deleted switches
            delete_switch_from_db = delete_switches_from_db(switches_to_delete)
            if delete_switch_from_db['status'] == "error":
                progress_recorder.stop_task(0, 100, 'Failed! unable to delete entries from DB')
                raise Exception(delete_switch_from_db['res'])

            # insert to DB
            write_switch_to_db = write_switches_to_db(switchtes_to_add)
            if write_switch_to_db['status'] == "error":
                progress_recorder.stop_task(0, 100, 'Failed! unable to write to DB')
                raise Exception(write_switch_to_db['res'])

        # keep track of iterations after switches are processed
        switch_db_counter = item_counter

        # --------------------- machines -------------------------------------------
        for machines in inputs['machines']:

            # increment counter for each iteration
            # index of current iteration
            # calculate percentage
            item_counter += 1
            index = inputs['machines'].index(machines)
            percent = (index + 1 + switch_db_counter) / total_no_items * 100

            # ------------------ Edit ----------------------------------
            # edit name, cpu, ram, NIC
            if machines['activity'] == 'edit':
                # fetch machine data from DB
                try:
                    machine_data = MachineModel.objects.get(machine_id=machines['machine_id']).__dict__
                    # get existing number of NICs and NIC JSON
                    current_nic_count = machine_data['nics']
                    current_nic_json_str = machine_data['switch_nic']

                    # convert raw str from DB to dict
                    current_nic_json = eval(current_nic_json_str)
                    current_machine_name = machine_data['machine_name']

                    # dict to update DB
                    machine_db_edits = {
                        "machine_id": machines['machine_id']
                    }

                    # temp
                    print('Editing machine {}'.format(machine_data['machine_name']))
                    progress_recorder.set_progress(percent, 100, description='Editing machine {} <br>'.
                                                   format(machine_data['machine_name']))

                    # --------------- rename ----------------------------
                    if "machine_name" in machines:
                        rename_vm = machine_helper.rename_vm(
                            service_instance,
                            current_machine_name,
                            machines['machine_name'],
                            default_values
                        )

                        # on success
                        if rename_vm['status'] == "success":
                            progress_recorder.set_progress(percent, 100, description='Renaming machine {}: Done!'.
                                                           format(machine_data['machine_name']))

                            # add to DB dict
                            # set new machine name, for use in upcoming processes
                            machine_db_edits["machine_name"] = machines['machine_name']
                            current_machine_name = machines['machine_name']

                            # update JSON
                            inputs['machines'][index]['status'] = 'success'
                            inputs['machines'][index]['activity'] = 'implement'
                        else:
                            # temp
                            progress_recorder.set_progress(percent, 100, description='Deleting machine {}: Failed!'.
                                                           format(machine_data['machine_name']))
                            # add to list
                            failed_machines.insert(len(failed_machines), machines['machine_id'])

                            # update JSON
                            inputs['machines'][index]['status'] = 'failed'
                            inputs['machines'][index]['activity'] = 'implement'
                            inputs['machines'][index]['message'] = rename_vm['res']

                    # --------------- edit settings ----------------------
                    machine_edits = {}
                    if "cpu" in machines:
                        machine_edits['cpu'] = machines['cpu']

                    if "ram" in machines:
                        machine_edits['ram'] = machines['ram']

                    if bool(machine_edits):
                        edit_vm = machine_helper.edit_vm_settings(
                            service_instance,
                            current_machine_name,
                            machine_edits,
                            default_values
                        )

                        # on success
                        if edit_vm['status'] == "success":

                            progress_recorder.set_progress(percent, 100, description='Editing machine {}: Done!'.
                                                           format(current_machine_name))

                            # DB dict
                            if "cpu" in machines:
                                machine_db_edits["cpus"] = machines['cpu']

                            if "ram" in machines:
                                machine_db_edits["ram"] = machines['ram']

                            # update JSON
                            inputs['machines'][index]['status'] = 'success'
                            inputs['machines'][index]['activity'] = 'implement'
                        else:
                            progress_recorder.set_progress(percent, 100, description='Editing machine {}: Failed!'.
                                                           format(current_machine_name))

                            # add to list
                            failed_machines.insert(len(failed_machines), machines['machine_id'])

                            # update JSON
                            inputs['machines'][index]['status'] = 'failed'
                            inputs['machines'][index]['activity'] = 'implement'
                            inputs['machines'][index]['message'] = edit_vm['res']

                    # ---------------------- add/remove NIC -------------------------
                    if "interfaces" in machines:
                        # add new NIC
                        # loop through each interface
                        for each_nic in machines['interfaces']:
                            if each_nic['action'] == 'edit':
                                # search for NIC id in DB
                                for each_db_nic in current_nic_json:
                                    if each_db_nic['name'] == each_nic['name']:
                                        # get NIC index
                                        split_name = each_nic['name'].split('_')
                                        nic_index = int(split_name[len(split_name) - 1])

                                        edit_nic = network_helper.edit_nic(
                                            service_instance,
                                            nic_index,
                                            each_nic['switch'],
                                            current_machine_name
                                        )

                                        if edit_nic['status'] == "success":
                                            for item in current_nic_json:
                                                if each_nic['name'] == item['name']:
                                                    # item_index = current_nic_json.index(item)
                                                    item['switch'] = each_nic['switch']
                                                    item['ip'] = each_nic['ip']
                                                    item['gateway'] = each_nic['gateway']
                                                    item['action'] = each_nic['action']

                                                    machine_db_edits['nics'] = current_nic_count
                                                    machine_db_edits['switch_nic'] = current_nic_json

                                            # update JSON
                                            inputs['machines'][index]['status'] = 'success'
                                            inputs['machines'][index]['activity'] = 'implement'
                                        else:
                                            # update JSON
                                            inputs['machines'][index]['status'] = 'failed'
                                            inputs['machines'][index]['activity'] = 'implement'
                                            inputs['machines'][index]['message'] = edit_nic['res']

                            if each_nic['action'] == 'add':
                                add_nic = network_helper.add_nic(
                                    service_instance,
                                    current_machine_name,
                                    each_nic['switch']
                                )

                                # on success, add to DB json object
                                if add_nic['status'] == "success":
                                    current_nic_json.insert(len(current_nic_json), each_nic)
                                    machine_db_edits['switch_nic'] = current_nic_json
                                    current_nic_count += 1
                                    machine_db_edits['nics'] = current_nic_count

                                    # update JSON (Added on 03-06-21 by dharmaraj)
                                    inputs['machines'][index]['status'] = 'success'
                                    inputs['machines'][index]['activity'] = 'implement'
                                else:
                                    # update JSON
                                    inputs['machines'][index]['status'] = 'failed'
                                    inputs['machines'][index]['activity'] = 'implement'
                                    inputs['machines'][index]['message'] = add_nic['res']

                            if each_nic['action'] == 'delete':

                                # search for NIC id in DB
                                for each_db_nic in current_nic_json:
                                    if each_db_nic['name'] == each_nic['name']:
                                        # get NIC index
                                        split_name = each_nic['name'].split('_')
                                        nic_index = int(split_name[len(split_name) - 1])

                                        delete_nic = network_helper.delete_nic(
                                            service_instance,
                                            current_machine_name,
                                            nic_index,
                                            default_values
                                        )

                                        if delete_nic['status'] == "success":
                                            for item in current_nic_json:
                                                if each_nic['name'] == item['name']:
                                                    item_index = current_nic_json.index(item)

                                                    del current_nic_json[item_index]
                                                    current_nic_count -= 1
                                                    machine_db_edits['nics'] = current_nic_count
                                                    machine_db_edits['switch_nic'] = current_nic_json

                                            # update JSON
                                            inputs['machines'][index]['status'] = 'success'
                                            inputs['machines'][index]['activity'] = 'implement'
                                        else:
                                            # update JSON
                                            inputs['machines'][index]['status'] = 'failed'
                                            inputs['machines'][index]['activity'] = 'implement'
                                            inputs['machines'][index]['message'] = delete_nic['res']

                    # add to list
                    edited_machines.insert(len(edited_machines), machine_db_edits)

                except MachineModel.DoesNotExist:
                    progress_recorder.set_progress(percent, 100, description='Edit machine {}: Failed!'.format(
                        inputs['machines'][index]['machine_name']))

                    # add to list
                    failed_machines.insert(len(failed_machines), machines['machine_id'])

                    # update JSON
                    inputs['machines'][index]['status'] = 'failed'
                    inputs['machines'][index]['activity'] = 'implement'
                    inputs['machines'][index]['message'] = 'Machine {} not found in DB'.format(machines['machine_id'])

            # -------------------Delete machine------------------------
            if machines['activity'] == 'delete':
                # fetch machine data from DB
                try:
                    machine_data = MachineModel.objects.get(machine_id=machines['machine_id']).__dict__

                    print('Deleting Machine {}'.format(machine_data['machine_name']))
                    response_message += 'Deleting Machine {} '.format(machine_data['machine_name'])
                    progress_recorder.set_progress(percent, 100, description='Deleting Machine {} '.
                                                   format(machine_data['machine_name']))

                    if machine_data['machine_name']:
                        delete_vm = machine_helper.delete_vm(
                            service_instance,
                            machine_data['machine_name'],
                            default_values
                        )

                        # on success
                        if delete_vm['status'] == "success":
                            progress_recorder.set_progress(percent, 100, description='Deleting machine {}: Done!'.
                                                           format(machine_data['machine_name']))

                            # add to list
                            deleted_machines.insert(len(deleted_machines), machines['machine_id'])

                            # update JSON
                            inputs['machines'][index]['status'] = 'success'
                            inputs['machines'][index]['activity'] = 'deleted'
                        else:
                            # temp
                            progress_recorder.set_progress(percent, 100, description='Deleting machine {}: Failed!'.
                                                           format(machine_data['machine_name']))
                            # add to list
                            failed_machines.insert(len(failed_machines), machines['machine_id'])

                            # update JSON
                            inputs['machines'][index]['status'] = 'failed'
                            inputs['machines'][index]['activity'] = 'deleted'
                            inputs['machines'][index]['message'] = delete_vm['res']

                    else:
                        progress_recorder.set_progress(percent, 100, description='Deleting machine {}: Failed!'.format(
                            machine_data['machine_name']))

                        # add to list
                        failed_machines.insert(len(failed_machines), machines['machine_id'])

                        # update JSON
                        inputs['machines'][index]['status'] = 'failed'
                        inputs['machines'][index]['activity'] = 'deleted'
                        inputs['machines'][index]['message'] = machine_data['machine_name'] + str(" does not exist")

                except MachineModel.DoesNotExist:

                    progress_recorder.set_progress(percent, 100, description='Deleting machine {}: Failed!'.format(
                        machines['machine_name']))

                    # add to list
                    failed_machines.insert(len(failed_machines), machines['machine_id'])

                    # update JSON
                    inputs['machines'][index]['status'] = 'failed'
                    inputs['machines'][index]['activity'] = 'implement'
                    inputs['machines'][index]['message'] = 'Machine {} not found in DB'.format(machines['machine_id'])

            # -------------------Add Machine--------------------------------
            if machines['activity'] == 'new':
                # success flag
                machine_success_flag = False

                # machine parameters
                cpu = machines['cpu']
                ram = machines['ram']
                hdd = machines['hdd']
                iso_path = machines['iso_path']
                vm_obj = None
                no_of_nics = 0
                vm_name = machines['machine_name']
                failure_messages = ''

                # initialize dict to insert to DB
                db_insert = {
                    "machine_id": machines['machine_id'],
                    "machine_name": vm_name,
                    "cpu": cpu,
                    "ram": ram,
                    "hard_disk": hdd,
                    "iso_path": iso_path,
                    "nics": no_of_nics,
                    "nic_json": [],
                    "machine_type": 'custom',
                    "machine_category": machines['type']
                }

                # check if VM already exists in DB, using machine_id
                try:
                    search_db = MachineModel.objects.get(machine_id=machines['machine_id']).__dict__

                    print(vm_name + " machine exist already in DB")

                    # temp
                    progress_recorder.set_progress(percent, 100, description='Machine {} already exists!'.format(vm_name))

                    # add to failed list
                    failed_machines.insert(len(failed_machines), vm_name)

                    # update JSON
                    inputs['machines'][index]['status'] = 'failed'
                    inputs['machines'][index]['activity'] = 'implement'
                    inputs['machines'][index]['message'] = 'Machine {} already exists!'.format(vm_name)

                except MachineModel.DoesNotExist:
                    # create a VM
                    if machines['endpoint_type'] == 'custom_endpoint':
                        create_machine = machine_helper.create_vm(
                            service_instance,
                            vm_name,
                            cpu,
                            ram,
                            machines['guest_id'],
                            default_values
                        )

                        if create_machine['status'] == "success":
                            # set success flag
                            print("machine created by ekta")
                            machine_success_flag = True

                            # add CD ROM and HDD using vm object
                            vm_obj_response = vm_helper.get_vm_obj(vm_name, datacenter_name, host_name, resource_pool_name)
                            if vm_obj_response['status'] == "success":
                                vm_obj = vm_obj_response['res']
                                # add hard disk & CD ROM
                                add_ide = disk_helper.add_scsi_controller(vm_obj)
                                add_cd_rom = disk_helper.add_cd_rom_iso(service_instance, vm_obj, iso_path)
                                add_disk = disk_helper.add_hard_disk(vm_obj, hdd)

                                if add_ide['status'] != "success" or add_cd_rom['status'] != "success" or add_disk['status'] != "success":
                                    # set success flag
                                    machine_success_flag = False

                                    if add_ide['status'] == "error":
                                        # set failure message
                                        failure_messages += add_ide['res'] + '. '
                                    elif add_cd_rom['status'] == "error":
                                        failure_messages += add_cd_rom['res'] + '. '
                                    else:
                                        failure_messages += add_disk['res'] + '. '

                                else:
                                    progress_recorder.set_progress(percent, 100,
                                                                   description='Creating machine {}: Done!'.format(vm_name))
                                    # add to list for DB
                                    db_insert['guest_id'] = machines['guest_id']
                                    db_insert['template'] = 'NA'

                            # if failed to fetch the vm object
                            else:
                                # set success flag
                                machine_success_flag = False

                                # set failure message
                                failure_messages += vm_obj_response['res'] + '. '
                        else:
                            progress_recorder.set_progress(percent, 100, description='Creating machine {}: Failed!'.
                                                           format(vm_name))

                            # set success flag
                            machine_success_flag = False

                            # set failure message
                            failure_messages += create_machine['res'] + '. '

                    # clone a VM
                    if machines['endpoint_type'] == 'template_endpoint':

                        clone_machine = machine_helper.clone_from_template(
                            service_instance,
                            vm_name,
                            machines['guest_id'],
                            default_values
                        )

                        if clone_machine["status"] == "success":
                            # set success flag
                            machine_success_flag = True
                            progress_recorder.set_progress(percent, 100, description='Cloning machine {}: Done!'.
                                                           format(vm_name))

                            # DB data
                            db_insert['guest_id'] = 'NA'
                            db_insert['template'] = machines['guest_id']

                        else:
                            # temp
                            progress_recorder.set_progress(percent, 100, description='Cloning machine {}: Failed!'
                                                           .format(vm_name))
                            # set success flag
                            machine_success_flag = False
                            # set failure messages
                            failure_messages += clone_machine['res'] + '. '

                    # add NIC(s)
                    if len(machines['interfaces']) is not 0:
                        t = 0
                        # loop through each interface
                        for each_nic in machines['interfaces']:
                            t = t + 1
                            if machines['endpoint_type'] == 'template_endpoint' and t == 1:
                                # get NIC index
                                split_name = each_nic['name'].split('_')
                                nic_index = int(split_name[len(split_name) - 1])
                                if nic_index == 1:
                                    add_or_edit_nic = network_helper.edit_nic(service_instance, nic_index,
                                                                              each_nic['switch'], vm_name)
                                    delete_nic = {
                                        "status": "success"
                                    }
                                else:
                                    add_or_edit_nic = network_helper.add_nic(service_instance, vm_name,
                                                                             each_nic['switch'])
                                    delete_nic = network_helper.delete_nic(service_instance, vm_name, 1, default_values)

                            else:
                                add_or_edit_nic = network_helper.add_nic(service_instance, vm_name, each_nic['switch'])
                                delete_nic = {
                                    "status": "success"
                                }

                            # on success, add to DB json object
                            if (add_or_edit_nic['status'] == "success") and (delete_nic['status'] == "success"):
                                db_insert['nics'] += 1
                                db_insert['nic_json'].insert(len(db_insert['nic_json']), each_nic)
                            else:
                                # set success flag and failure messaage
                                machine_success_flag = False
                                if delete_nic['status'] == "error" and add_or_edit_nic['status'] == "error":
                                    failure_messages += add_or_edit_nic['res'] + " / " + delete_nic['res']
                                elif delete_nic['status'] == "error":
                                    failure_messages += delete_nic['res'] + "."
                                else:
                                    failure_messages += add_or_edit_nic['res'] + "."

                    # if creation or cloning fails due to any reason, attempt to delete VM
                    # if machine_success_flag is False delete vm
                    if machine_success_flag is False:
                        delete_vm = machine_helper.delete_vm(
                            service_instance,
                            vm_name,
                            default_values
                        )

                        # add to failed list
                        failed_machines.insert(len(failed_machines), vm_name)
                        # update JSON
                        inputs['machines'][index]['status'] = 'failed'
                        inputs['machines'][index]['activity'] = 'implement'

                        if delete_vm['status'] == "success":
                            inputs['machines'][index]['message'] = failure_messages
                        else:
                            inputs['machines'][index]['message'] = failure_messages + " VM might be corrupted, " \
                                                                   "please delete it from vsphere and try again"

                    else:
                        new_machines.insert(len(new_machines), db_insert)

                        # update JSON
                        inputs['machines'][index]['status'] = 'success'
                        inputs['machines'][index]['activity'] = 'implement'

        # update DB
        if len(inputs['machines']) > 0:
            # increment counter for each iteration
            item_counter += 1

            # percent
            percent = item_counter / total_no_items * 100
            progress_recorder.set_progress(percent, 100, description='Writing changes to DB')

            # deleted machines
            if len(deleted_machines) > 0:
                delete_from_db = delete_machines_from_db(deleted_machines)
                if delete_from_db['status'] == "error":
                    progress_recorder.set_progress(percent, 100, description='Writing changes to DB')
                    inputs['error'] = 'Exception occurred while deleting entries from DB.' + delete_from_db['res']
                    return inputs

            # edited machines
            if len(edited_machines) > 0:
                edit_machines_in_db = edit_machine_db_entries(edited_machines)
                if edit_machines_in_db['status'] == "error":
                    progress_recorder.set_progress(percent, 100, description='Writing changes to DB')
                    inputs['error'] = 'Exception occurred while updating entries to DB.' + edit_machines_in_db['res']
                    return inputs

            # new machines
            if len(new_machines) > 0:
                insert_new_to_db = write_machines_to_db(new_machines)
                if insert_new_to_db['status'] == "error":
                    progress_recorder.set_progress(percent, 100, description='Writing changes to DB')
                    inputs['error'] = 'Exception occurred while adding entries to DB.' + insert_new_to_db['res']
                    return inputs

        progress_recorder.set_progress(100, 100, description='Complete!')

        # logout
        vm_helper.vm_logout(service_instance)
        return inputs

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        # write to log file
        with open(_log_files['error'], 'a', newline='') as errorFile:
            errorFile.write(str(exc_type))
            errorFile.write(str(exc_obj))
            errorFile.write(str(exc_tb))

        # temp
        progress_recorder.set_progress(0, 100, 'Failed due to an error!')

        inputs['error'] = 'Exception occurred.' + str(e)
        return inputs
    except None as e:
        inputs["error"] = 'Exception occurred.' + str(e)
        return inputs


###############################################################
# ------------------------DB Function -------------------------------

def get_default_values_from_db():
    return {
        'esxi_host': settings.VS_HOST,
        'switch_ports': 24,
        'data_center': settings.VS_DC,
        'resource_pool': settings.VS_RPS,
        'folder': None,
        'data_store_name': settings.VS_DS,
        'cluster': '',
        'data_store_cluster': '',
        'vm_version': 'vmx-11'
    }


def write_switches_to_db(successful_switches):
    """
    :param successful_switches: list
    :return:
    """
    try:
        objs = [
            SwitchModel(
                switch_name=each['switch_name'],
                port_group_name=each['port_group_name'],
                subnet=each['subnet'],
                switch_id=each['switch_id']
            )
            for each in successful_switches
        ]
        SwitchModel.objects.bulk_create(objs)
        response_message = " Switch saved to db"
        _json = {
            'res': response_message,
            'status': "success"
        }
        return _json

    except Exception as db_exception:
        response_message = "Exception occurred while updating DB with switch details." + str(db_exception)
        _json = {
            'res': response_message,
            'status': "error"
        }
        return _json


def write_machines_to_db(successful_machines):
    """
        :param successful_machines:
        :return:
        """
    try:
        objs = [
            MachineModel(
                machine_id=each['machine_id'],
                machine_name=each['machine_name'],
                cpus=each['cpu'],
                ram=each['ram'],
                hard_disk=each['hard_disk'],
                iso_path=each['iso_path'],
                nics=each['nics'],
                switch_nic=each['nic_json'],
                machine_type=each['machine_type'],
                machine_category=each['machine_category'],
                guest_id=each['guest_id'],
                template=each['template']
            )
            for each in successful_machines
        ]
        MachineModel.objects.bulk_create(objs)
        _json = {
            "status": "success",
            "res": " Machine added to the DB"
        }
        return _json

    except Exception as db_exception:
        _json = {
            "status": "error",
            "res": str(db_exception)
        }
        return _json


def edit_machine_db_entries(list_of_edited_machines):
    try:
        for each in list_of_edited_machines:
            db_dict = each

            if 'activity' in db_dict:
                del db_dict['activity']

            MachineModel.objects.filter(machine_id=db_dict['machine_id']).update(**db_dict)

        _json = {
            "status": "success",
            "res": " Machine details updated to the DB"
        }
        return _json

    except Exception as db_exception:
        _json = {
            "status": "error",
            "res": str(db_exception)
        }
        return _json


def delete_switches_from_db(list_of_switches):
    try:
        for each in list_of_switches:
            SwitchModel.objects.filter(switch_id=each).delete()
        _json = {
            "status": "success",
            "res": " Switch details deleted from the DB"
        }
        return _json
    except Exception as db_exception:
        _json = {
            "status": "error",
            "res": str(db_exception)
        }
        return _json


def delete_machines_from_db(list_of_machines):
    try:
        for each in list_of_machines:
            MachineModel.objects.filter(machine_id=each).delete()

        _json = {
            "status": "success",
            "res": " Machine details deleted from the DB"
        }
        return _json
    except Exception as db_exception:
        _json = {
            "status": "error",
            "res": str(db_exception)
        }
        return _json

###############################################################


def processor(request):
    # get JSON input (from file)
    inputs = read_json_input()
    result = None


    i = app.control.inspect()
    celery_status = i.ping()

    if bool(celery_status) is True:
        # check for changes
        if 'changes' in inputs:
            if len(inputs['changes']['switches']) > 0 or len(inputs['changes']['machines']) > 0:
                # update topology
                response = topology.delay(inputs['changes'], username=request.user.username)
                result = response.id
                print("its in edit loop")

        if ('switches' in inputs) or ('machines' in inputs):
            if len(inputs['switches']) > 0 or len(inputs['machines']) > 0:
                # create topology
                response = topology.delay(inputs, username=request.user.username)
                result = response.id
                print("its in create loop")

        json_ = {
            'res': result,
            'status': 'success'
        }

        return JsonResponse(json_, safe=False)
    else:
        json_ = {
            'res': 'Critical processes are down. Please try again or contact support.',
            'status': 'error'
        }

        return JsonResponse(json_, safe=False)


def read_json_input():
    folder = os.path.join(settings.MEDIA_ROOT, 'topology/')
    file_json = os.path.join(settings.MEDIA_ROOT, 'topology', 'temp.json')
    json_file = {}
    if os.path.isfile(folder + 'topology.json'):
        if os.path.isfile(folder + 'temp.json'):
            with open(file_json, "r", encoding='utf-8') as out:
                out.seek(0)
                temp_json = json.loads(out.read())
                temp_json_change = temp_json['changes']
                json_file['changes'] = temp_json_change
        else:
            json_file = {}
    else:
        if os.path.isfile(folder + 'temp.json'):
            with open(file_json, "r", encoding='utf-8') as out:
                out.seek(0)
                json_file = json.loads(out.read())
        else:
            json_file = {}

    return json_file


