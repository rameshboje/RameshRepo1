from django.urls import path
from . import views
from . import take_browser_console_cred, snapshot_operations, template_operations

'''
return routes related to credentials app

main url: http://ip-address:port/credentials/

To use url in ajax calls, url should be followed by main url
Eg:  tableData 

'''


urlpatterns = [
    # main route to the credentials page
    path('', views.index, name='credentials'),

    # ajax route to initialize table
    path('credentials-machine-table', views.credentials_machines_table, name='credentials_machines_table'),
    path('edit-machine', views.edit_credential, name='edit_credential'),
    path('delete-machine', views.delete_credential, name='delete_credential'),
    path('add-machine', views.add_credential, name='add_credential'),
    path('fetch-vsphere', views.fetch_exsi_credentials, name='fetch_exsi_credentials'),

    # download pdf route
    # path('download_pdf', views.download_pdf, name='download_credentials_pdf')
    path('take-browser-console-cred', take_browser_console_cred.lanch_vm_console_cred, name='lanch_vm_console_cred'),

    # Snapshots URLs
    path('take-machine-snapshot', snapshot_operations.take_machine_snapshot, name='take_machine_snapshot'),
    path('delete-machine-snapshots', snapshot_operations.delete_machine_snapshots, name='delete_machine_snapshots'),
    path('revert-machine-snapshot', snapshot_operations.revert_machine_snapshot, name='revert_machine_snapshot'),

    # Template URLs
    path('create-machine-template', template_operations.create_machine_template, name='create_machine_template'),
    path('delete-machine-templates', template_operations.delete_machine_templates, name='delete_machine_templates'),

]
