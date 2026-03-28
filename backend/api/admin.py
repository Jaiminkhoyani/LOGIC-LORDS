"""
LiveStock IQ — Django Admin Registration
"""

from django.contrib import admin
from .models import Farm, Cattle, SensorDevice, Alert, VetRecord, AlertThreshold


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display  = ['name', 'owner', 'location', 'state', 'created_at']
    search_fields = ['name', 'owner__username', 'location']


@admin.register(Cattle)
class CattleAdmin(admin.ModelAdmin):
    list_display  = ['cattle_id', 'name', 'breed', 'status', 'temperature', 'activity', 'feeding', 'farm', 'updated_at']
    list_filter   = ['status', 'breed', 'lactating', 'sex', 'farm']
    search_fields = ['cattle_id', 'name', 'breed']
    ordering      = ['cattle_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SensorDevice)
class SensorDeviceAdmin(admin.ModelAdmin):
    list_display  = ['device_uid', 'cattle', 'status', 'battery_pct', 'signal_strength', 'last_ping']
    list_filter   = ['status']
    search_fields = ['device_uid', 'cattle__name']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ['title', 'cattle', 'alert_type', 'is_resolved', 'created_at']
    list_filter   = ['alert_type', 'is_resolved']
    search_fields = ['title', 'cattle__name', 'cattle__cattle_id']
    ordering      = ['-created_at']
    readonly_fields = ['created_at']
    actions       = ['mark_resolved']

    @admin.action(description='Mark selected alerts as resolved')
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now(), resolved_by=request.user)


@admin.register(VetRecord)
class VetRecordAdmin(admin.ModelAdmin):
    list_display  = ['cattle', 'record_type', 'diagnosis', 'vet_name', 'cost', 'created_at']
    list_filter   = ['record_type']
    search_fields = ['cattle__name', 'diagnosis', 'vet_name']


@admin.register(AlertThreshold)
class AlertThresholdAdmin(admin.ModelAdmin):
    list_display  = ['farm', 'high_temp', 'low_temp', 'min_activity', 'min_feeding', 'updated_at']


# Customise admin header
admin.site.site_header  = '🐄 LiveStock IQ — Admin Panel'
admin.site.site_title   = 'LiveStock IQ'
admin.site.index_title  = 'Farm Management Dashboard'
