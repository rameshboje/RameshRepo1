from django.urls import path
from . import views
from . import node_validator
from . import simulation, progress
from . import database
from .canvas import processor

'''
return routes related to dashboard app

main url: http://ip-address:port/dashboard/

'''


urlpatterns = [
    # main route to the dashboard page
    path('', simulation.index, name='canvas'),

    path('progress', progress.canvas_progress, name='canvas_progress'),
    path('progress/all-tasks', progress.get_all_progress, name='get_all_progress'),
    path('progress/delete-progress', progress.delete_progress, name='delete_progress'),

    path('fetch-topology', simulation.fetch_topology, name='fetch_topology'),
    path('validate-before-publish', simulation.validate_before_publish, name='validate_before_publish'),
    path('check-implemented-status', simulation.check_implemented_status, name='check_implemented_status'),
    path('fetch-switch', simulation.fetch_switch_if_implemented, name='fetch_switch_if_implemented'),

    path('save-topology', simulation.save_topology, name='save_topology'),
    path('save-implemented-result', simulation.save_implemented_result, name='save_implemented_result'),
    path('get-task-progress', simulation.get_task_result, name='get_task_result'),
    path('create-topology', processor, name='processor'),
    # path('create-topology', simulation.create_topology, name='get_task_result'),
    path('fetch-machine', simulation.fetch_machine_if_implemented, name='fetch_machine_if_implemented'),
    path('fetch-machine-to-delete', simulation.fetch_machine_to_delete_implemented,
         name='fetch_machine_to_delete_implemented'),
    path('fetch-switch-to-delete', simulation.fetch_switch_to_delete_implemented,
         name='fetch_machine_to_delete_implemented'),
    path('open-console-in-browser', simulation.open_console_in_browser,
         name='open_console_in_browser'),
    # path('create-topology', simulation.create_topology, name='get_task_result'),


    #Validators
    path('validate-switch', node_validator.check_switch_ip_subnet_is_valid, name='check_switch_ip_subnet_is_valid'),
    path('validate-machine', node_validator.check_machine_is_valid, name='check_machine_is_valid'),

    # database
    path('fetch-guest-id',database.fetch_guestid,name='guest_ids'),
    path('fetch-switches', database.fetch_switches, name='fetch_switches'),
    path('fetch-templates', database.fetch_templates, name='fetch_templates'),

    # notification
    path('fetch-notification', views.fetch_canvas_notification, name='fetch_canvas_notification'),







    # path('save-topology', views.save_topology, name='save_topology'),
    # path('fetch-topology', views.fetch_topology, name='fetch_topology'),
    # path('implement-topology', views.implement_topology, name='implement_topology'),
    # path('fetch-saved-topology', views.fetch_saved_topology, name='fetch_saved_topology'),
    # path('create-topology', views.processor, name='processor'),
    # path('save-topology-publish', views.save_topology_publish, name='save-topology-publish'),
    # path('implemented-result', views.fetch_implemented_result, name='fetch_implemented_result'),
    # path('canvas_', views.canvas_, name='dashboard'),


    # Validators
    # path('validate-switch', node_validator.check_switch_ip_subnet_is_valid, name='check_switch_ip_subnet_is_valid'),
]