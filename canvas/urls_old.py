from django.urls import path
from . import views
from .canvas import processor

'''
return routes related to dashboard app

main url: http://ip-address:port/dashboard/

'''


urlpatterns = [
    # main route to the dashboard page
    path('', views.index, name='canvas'),
    path('save-topology', views.save_topology, name='save_topology'),
    path('fetch-topology', views.fetch_topology, name='fetch_topology'),
    path('implement-topology', views.implement_topology, name='implement_topology'),
    path('fetch-saved-topology', views.fetch_saved_topology, name='fetch_saved_topology'),
    path('create-topology', processor, name='processor'),
    path('save-topology-publish', views.save_topology_publish, name='save-topology-publish'),
    path('implemented-result', views.fetch_implemented_result, name='fetch_implemented_result'),
    # path('canvas_', views.canvas_, name='dashboard'),
]