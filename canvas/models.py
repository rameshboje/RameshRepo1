from django.db import models
from datetime import datetime
from django.utils import timezone


class CustomMachines(models.Model):
    machine_id = models.CharField(primary_key=True, unique=True, max_length=255)
    machine_name = models.CharField(max_length=255, unique=True)
    cpus = models.IntegerField(null=True)
    ram = models.IntegerField(null=True)
    hard_disk = models.IntegerField(null=True)
    iso_path = models.CharField(null=True, max_length=255)

    nics = models.IntegerField()
    switch_nic = models.TextField(null=True)

    machine_type = models.CharField(blank=False, max_length=255)
    machine_category = models.CharField(blank=False, max_length=255)
    guest_id = models.CharField(max_length=255)
    template = models.CharField(max_length=255)

    country_code = models.CharField(max_length=255)
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now())


class MachineTemplates(models.Model):
    template_name = models.CharField(unique=True, max_length=100)
    template_os = models.CharField(max_length=100)
    os_version = models.CharField(max_length=100)
    ip_change_support = models.BooleanField(default=False)


class VMGuestId(models.Model):
    name = models.CharField(max_length=30, unique=True, blank=False)
    description = models.CharField(max_length=191, blank=False, default="NA")


class VirtualSwitches(models.Model):
    switch_name = models.CharField(max_length=255, unique=True)
    switch_id = models.CharField(unique=True, max_length=255)
    port_group_name = models.CharField(unique=True, max_length=255)
    colour = models.CharField(max_length=255)
    subnet = models.GenericIPAddressField()
    ports = models.IntegerField(default=20)
    promiscuous = models.BooleanField(default=True)


class VsphereParameters(models.Model):
    data_center = models.CharField(max_length=255)
    data_source = models.CharField(max_length=255)
    resource_pool = models.CharField(max_length=255)
    cluster = models.CharField(max_length=255)
    total_cpu = models.IntegerField()
    total_ram = models.IntegerField()
    total_hard_disk = models.IntegerField()
    esxi_host = models.CharField(max_length=255)
    switch_ports = models.IntegerField()

#
# class DefaultValues(models.Model):
#     parameter = models.CharField(max_length=255)
#     value = models.CharField(max_length=255)
