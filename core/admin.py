from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User,AdminUser

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'is_verified', 'created_at']
    list_filter = ['role', 'is_verified', 'created_at']
    search_fields = ['username', 'email', 'full_name', 'company_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'full_name', 'phone', 'is_verified')
        }),
        ('Job Seeker Info', {
            'fields': ('skills', 'experience', 'resume')
        }),
        ('Company Info', {
            'fields': ('company_name', 'company_description', 'website')
        }),
    )



@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'department']
    search_fields = ['user__username']
