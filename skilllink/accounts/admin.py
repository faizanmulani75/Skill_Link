from django.contrib import admin
from .models import Profile, Transaction, Notification
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

class NotificationInline(admin.TabularInline):
    model = Notification
    extra = 1
    fields = ('title', 'body', 'link', 'is_read', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "tokens_balance",
        "location",
        # "tokens"
        "verified",
    )
    search_fields = ("user__username", "bio", "user__email")
    list_editable = ("verified",)
    ordering = ("user__username",)

# Extend UserAdmin to include notifications
admin.site.unregister(User)
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [NotificationInline]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "transaction_type", "timestamp", "description")
    list_filter = ("transaction_type", "timestamp")
    search_fields = ("user__user__username", "description")
    ordering = ("-timestamp",)
