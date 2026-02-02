from django.contrib import admin
from .models import Booking, BookingHistory, Report, Review, Message
from django.utils.html import format_html

# ---------------- BOOKING ADMIN ----------------
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requester",
        "provider",
        "skill",
        "status",
        "tokens_spent",
        "tokens_scheduled_given",
        "tokens_completed_given",
        "proposed_time",
        "meeting_link",
        "updated_at",
    )
    list_filter = ("status", "tokens_scheduled_given", "tokens_completed_given")
    search_fields = (
        "requester__user__username",
        "provider__user__username",
        "skill__name",
    )
    ordering = ("-updated_at",)
    readonly_fields = ("requested_at", "updated_at", "tokens_released", "review_pending")

    def meeting_link_display(self, obj):
        if obj.meeting_link:
            return format_html('<a href="{}" target="_blank">Join Zoom</a>', obj.meeting_link)
        return "No link"
    meeting_link_display.short_description = "Meeting Link"

# ---------------- BOOKING HISTORY ADMIN ----------------
@admin.register(BookingHistory)
class BookingHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "proposer",
        "proposed_time",
        "created_at",
    )
    search_fields = (
        "booking__id",
        "proposer__user__username",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

# ---------------- REPORT ADMIN ----------------
from django.shortcuts import render
from django.http import HttpResponseRedirect
from accounts.models import Notification

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_profile', 'booking', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reporter__user__username', 'reported_profile__user__username', 'reason')
    readonly_fields = ('reporter', 'reported_profile', 'booking', 'reason', 'created_at', 'notification_history')
    fields = ('reporter', 'reported_profile', 'booking', 'reason', 'admin_action_message', 'notification_history', 'created_at')

    def notification_history(self, obj):
        if not obj.reporter:
            return "No reporter found."
        notifications = Notification.objects.filter(user=obj.reporter.user).order_by('-timestamp')[:5]
        if not notifications:
            return "No previous notifications sent."
        
        html = "<ul>"
        for n in notifications:
            html += f"<li><strong>{n.timestamp.strftime('%Y-%m-%d %H:%M')}</strong>: {n.body}</li>"
        html += "</ul>"
        return format_html(html)
    notification_history.short_description = "Recent Notifications to Reporter"

    def save_model(self, request, obj, form, change):
        # Check if there's a new admin action message to send
        if obj.admin_action_message and obj.admin_action_message.strip():
            Notification.objects.create(
                user=obj.reporter.user,
                title="Admin Message regarding your report",
                body=obj.admin_action_message,
                link="/meetings/reports/"
            )
        super().save_model(request, obj, form, change)

    def message_reporter(self, request, queryset):
        for report in queryset:
            Notification.objects.create(
                user=report.reporter.user,
                title="Update on your report",
                body=f"Admin has reviewed your report against {report.reported_profile.user.username}.",
                link="/meetings/reports/"
            )
        self.message_user(request, "Notification sent to reporters.")
    message_reporter.short_description = "Send generic update to Reporter"

    def message_reported(self, request, queryset):
        for report in queryset:
            Notification.objects.create(
                user=report.reported_profile.user,
                title="Report filed against you",
                body="An administrator is reviewing a report regarding your recent activity. Please ensure you follow the community guidelines.",
                link=None
            )
        self.message_user(request, "Notification sent to reported users.")
    message_reported.short_description = "Send warning to Reported User"

# ---------------- REVIEW ADMIN ----------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('booking', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('booking__requester__user__username', 'booking__provider__user__username', 'comment')
    readonly_fields = ('created_at',)

# ---------------- MESSAGE ADMIN ----------------
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'booking', 'timestamp', 'is_read')
    list_filter = ('timestamp', 'is_read')
    search_fields = ('sender__user__username', 'content')
    readonly_fields = ('timestamp',)
