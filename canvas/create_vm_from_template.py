import atexit
import time
import ssl
from pyVim import connect
from pyVmomi import vim, vmodl


inputs = {'vcenter_ip': '192.168.15.134',
          'vcenter_password': 'P@ssw0rd@123',
          'vcenter_user': 'aruns@vsphere.local',
          # 'networks': "Zone6_46.148.22.0/24",
          'networks': "",
          'vm_name': "test_new_VM",
          'resource_pool': 'Ekta',
          'template': "Windows 10 ekta",
          'vm_folder': "",
          'datastore_name': "",
          'datacenter_name': "QOS (Bangalore)",
          'cluster_name': "",
          'datastorecluster_name': ""
          }


def wait_for_task(task, actionName='job', hideResult=False):
    """
    Waits and provides updates on a vSphere task
    """

    while task.info.state == vim.TaskInfo.State.running or task.info.state == vim.TaskInfo.State.queued:
        time.sleep(2)

    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = '%s completed successfully, result: %s' % (actionName, task.info.result)
            print(out)
        else:
            out = '%s completed successfully.' % actionName
            print(out)
    else:
        out = '%s did not complete successfully: %s' % (actionName, task.info.error)
        print(out)
        raise task.info.error  # error happens here

    return task.info.result


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def clone_vm(content, template, vm_name):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    # if none git the first one
    datacenter_name = inputs['datacenter_name']
    if datacenter_name is not "":
        datacenter = get_obj(content, [vim.Datacenter], inputs['datacenter_name'])
    else:
        datacenter = content.rootFolder.childEntity[0]

    vm_folder = inputs['vm_folder']
    if vm_folder is not "":
        destfolder = get_obj(content, [vim.Folder], vm_folder)
    else:
        destfolder = datacenter.vmFolder

    # datastore name
    datastore_name = inputs['datastore_name']
    if datastore_name is not "":
        datastore = get_obj(content, [vim.Datastore], datastore_name)
    else:
        datastore = get_obj(content, [vim.Datastore], template.datastore[0].info.name)

    # if None, get the first one
    cluster = get_obj(content, [vim.ClusterComputeResource], inputs['cluster_name'])
    resource_pool = inputs['resource_pool']
    if resource_pool is not "":
        resource_pool = get_obj(content, [vim.ResourcePool], resource_pool)
    else:
        resource_pool = cluster.resourcePool

    vmconf = vim.vm.ConfigSpec()

    datastorecluster_name = inputs['datastorecluster_name']
    if datastorecluster_name is not "":
        podsel = vim.storageDrs.PodSelectionSpec()
        pod = get_obj(content, [vim.StoragePod], datastorecluster_name)
        podsel.storagePod = pod

        storagespec = vim.storageDrs.StoragePlacementSpec()
        storagespec.podSelectionSpec = podsel
        storagespec.type = 'create'
        storagespec.folder = destfolder
        storagespec.resourcePool = resource_pool
        storagespec.configSpec = vmconf

        try:
            rec = content.storageResourceManager.RecommendDatastores(
                storageSpec=storagespec)
            rec_action = rec.recommendations[0].action[0]
            real_datastore_name = rec_action.destination.name
        except:
            real_datastore_name = template.datastore[0].info.name

        datastore = get_obj(content, [vim.Datastore], real_datastore_name)

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    # clonespec.powerOn = inputs['power_on']

    # TEMP:
    print('Cloning from template')
    
    task = template.Clone(folder=destfolder, name=vm_name, spec=clonespec)
    wait_for_task(task)


def begin_clone():

    # Disabling SSL certificate verification
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE

    # TEMP:
    print('Logging into vCenter host ' + inputs['vcenter_ip'])

    # si = connect.SmartConnectNoSSL(host=inputs['vcenter_ip'], user=inputs['vcenter_user'],
    #                                pwd=inputs['vcenter_password'])

    si = connect.SmartConnect(host=inputs['vcenter_ip'], user=inputs['vcenter_user'], pwd=inputs['vcenter_password'], sslContext=context)

    atexit.register(connect.Disconnect, si)

    # TEMP:
    print('Retrieving template ' + inputs['template'])

    content = si.RetrieveContent()
    template = get_obj(content, [vim.VirtualMachine], inputs['template'])

    if template:
        clone_vm(content, template, inputs['vm_name'])
    else:
        print("template not found")
