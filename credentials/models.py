from django.db import models
from django.utils import timezone
from jsonfield import JSONField
# from django_mysql.models import JSONField

"""
Credential table with column details
If required, add or modify the fields to create a table.
This model is used in credential views

"""


class Credential(models.Model):
    ip = models.GenericIPAddressField(unique=True, max_length=128)
    rdp_ip = models.GenericIPAddressField(unique=True, max_length=128, null=True)
    username = models.CharField(max_length=30, blank=False)
    password = models.CharField(max_length=30, blank=False)
    machine_name = models.CharField(max_length=30, blank=False, unique=True)
    connect_via = models.CharField(max_length=191, blank=False, default="NA")
    description = models.CharField(max_length=255, blank=False, default="NA")
    snap_shot_name = models.CharField(max_length=191, blank=False, default="NA")
    machine_used = models.TextField(blank=False, default="NA")
    is_reverted = models.CharField(max_length=191, blank=False, default="Visible")
    os = models.CharField(max_length=191,blank=False, default="NA")
    machine_type = models.CharField(max_length=191, blank=False, default="Visible")
    conn_name = models.CharField(max_length=200, blank=False, default="NA")
    host_conn_name = models.CharField(max_length=200, blank=False, default="NA")
    data_store = models.CharField(max_length=200, default="NA")
    data_center = models.CharField(max_length=200, default="NA")
    resource_pool = models.CharField(max_length=200, default="NA")
    host_domain = models.CharField(max_length=200, default="NA")
    host = models.GenericIPAddressField(max_length=128, default="NA")
    server_ip = models.GenericIPAddressField(max_length=128, default="NA")
    exsi_username = models.CharField(max_length=30, blank=False, default="NA")
    exsi_password = models.CharField(max_length=30, blank=False, default="NA")
    rdp_file_name = models.CharField(max_length=100, blank=False, default="NA")
    is_red_vs_blue = models.BooleanField(default=False)
    red_vs_blue_type = models.CharField(max_length=191, blank=False, default="NA")
    snapshot_details = JSONField(blank=True, null=True, default={})
    template_details = JSONField(blank=True, null=True, default={})
    created_at = models.DateTimeField(max_length=80, null=False, blank=False,default=timezone.now)
    updated_at = models.DateTimeField(max_length=80, null=False, blank=False,default=timezone.now)
