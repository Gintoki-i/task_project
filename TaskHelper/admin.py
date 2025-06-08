from django.contrib import admin
from .models import Employee, TaskRecord
from django.utils.safestring import mark_safe




@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'avatar_preview')
    readonly_fields = ('avatar_preview',)

    def avatar_preview(self, obj):
        try:
            return mark_safe(f'<img src="{obj.avatar.url}" width="40" height="40" style="border-radius:50%;">')
        except (ValueError, AttributeError):
            return mark_safe('<span style="color:gray;">无头像</span>')

    avatar_preview.short_description = '头像预览'


@admin.register(TaskRecord)
class TaskRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'completed', 'errors')
    list_filter = ('employee', 'date')
