from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import IdentityVerification, User

@admin.register(User)
class FasthomeUserAdmin(UserAdmin):
    ordering = ('-created_at',)
    list_display = ('fasthome_id', 'email', 'phone', 'last_name', 'first_name', 'is_certified', 'is_staff')
    search_fields = ('fasthome_id', 'email', 'phone', 'last_name', 'first_name')
    fieldsets = UserAdmin.fieldsets + (('Fasthome', {'fields': ('postname','birth_date','sex','profession','fasthome_id','is_phone_verified','is_email_verified','is_certified','profile_photo')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('email','phone','last_name','first_name')}),)

@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ('user','document_type','status','facial_status','submitted_at','verified_at')
    list_filter = ('status','facial_status','document_type')
    search_fields = ('user__fasthome_id','user__email')
