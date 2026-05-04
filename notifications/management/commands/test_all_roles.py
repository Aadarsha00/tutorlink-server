# notifications/management/commands/test_all_roles.py
"""
Quick test to send notifications to all roles
Usage: python manage.py test_all_roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.services import (
    NotificationService,
    SystemNotificationService,
)
from notifications.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = "Quick test to send notifications to all roles"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("🚀 TESTING NOTIFICATIONS FOR ALL ROLES"))
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))

        # Get one user from each role
        parent = User.objects.filter(role="parent", is_active=True).first()
        teacher = User.objects.filter(role="teacher", is_active=True).first()
        admin = User.objects.filter(role="admin", is_active=True).first()

        if not parent:
            self.stdout.write(self.style.ERROR("❌ No parent user found"))
        if not teacher:
            self.stdout.write(self.style.ERROR("❌ No teacher user found"))
        if not admin:
            self.stdout.write(self.style.ERROR("❌ No admin user found"))

        if not (parent or teacher or admin):
            self.stdout.write(
                self.style.ERROR("\n❌ No users found. Cannot run tests.\n")
            )
            return

        # Test 1: Send to PARENT
        if parent:
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"TEST 1: Sending notification to PARENT")
            self.stdout.write(f"User: {parent.email} (ID: {parent.id})")
            self.stdout.write(f"{'=' * 70}")

            notification = NotificationService.send_notification(
                user=parent,
                notification_type="test",
                title="Test for Parent",
                message="This is a test notification for a parent user. If you see this, notifications are working!",
                link="/parent/dashboard",
                metadata={"test": True, "role": "parent"},
            )

            self.stdout.write(
                self.style.SUCCESS(f"✅ Notification created: ID={notification.id}")
            )
            self.verify_notification(parent)

        # Test 2: Send to TEACHER
        if teacher:
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"TEST 2: Sending notification to TEACHER")
            self.stdout.write(f"User: {teacher.email} (ID: {teacher.id})")
            self.stdout.write(f"{'=' * 70}")

            notification = NotificationService.send_notification(
                user=teacher,
                notification_type="test",
                title="Test for Teacher",
                message="This is a test notification for a teacher user. If you see this, notifications are working!",
                link="/teacher/dashboard",
                metadata={"test": True, "role": "teacher"},
            )

            self.stdout.write(
                self.style.SUCCESS(f"✅ Notification created: ID={notification.id}")
            )
            self.verify_notification(teacher)

        # Test 3: Send to ADMIN
        if admin:
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"TEST 3: Sending notification to ADMIN")
            self.stdout.write(f"User: {admin.email} (ID: {admin.id})")
            self.stdout.write(f"{'=' * 70}")

            notification = NotificationService.send_notification(
                user=admin,
                notification_type="test",
                title="Test for Admin",
                message="This is a test notification for an admin user. If you see this, notifications are working!",
                link="/admin/dashboard",
                metadata={"test": True, "role": "admin"},
            )

            self.stdout.write(
                self.style.SUCCESS(f"✅ Notification created: ID={notification.id}")
            )
            self.verify_notification(admin)

        # Test 4: Send to ALL USERS
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"TEST 4: Broadcasting to ALL USERS")
        self.stdout.write(f"{'=' * 70}")

        notifications = SystemNotificationService.notify_all_users(
            title="System Test Broadcast",
            message="This is a broadcast notification sent to all active users!",
            link="/notifications",
        )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Broadcast sent to {len(notifications)} users")
        )

        # Summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(self.style.SUCCESS("📊 TEST SUMMARY"))
        self.stdout.write(f"{'=' * 70}")

        for role in ["parent", "teacher", "admin"]:
            users = User.objects.filter(role=role, is_active=True)
            total_notifs = Notification.objects.filter(user__in=users).count()
            unread_notifs = Notification.objects.filter(
                user__in=users, is_read=False
            ).count()

            self.stdout.write(f"\n{role.upper()}:")
            self.stdout.write(f"  Active users: {users.count()}")
            self.stdout.write(f"  Total notifications: {total_notifs}")
            self.stdout.write(f"  Unread notifications: {unread_notifs}")

        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ ALL TESTS COMPLETE - Check your frontend to verify!"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "\n💡 TIP: Open the app in different browser tabs logged in as different roles"
            )
        )
        self.stdout.write(
            self.style.WARNING("    and watch notifications appear in real-time!\n")
        )

    def verify_notification(self, user):
        """Verify notification was created correctly"""
        recent_notif = (
            Notification.objects.filter(user=user).order_by("-created_at").first()
        )

        if recent_notif:
            self.stdout.write(f"  📬 Latest notification:")
            self.stdout.write(f"     ID: {recent_notif.id}")
            self.stdout.write(f"     Type: {recent_notif.notification_type}")
            self.stdout.write(f"     Title: {recent_notif.title}")
            self.stdout.write(f"     Is Read: {recent_notif.is_read}")
            self.stdout.write(f"     Created: {recent_notif.created_at}")

            unread_count = Notification.objects.filter(user=user, is_read=False).count()
            self.stdout.write(f"  📊 Unread count: {unread_count}")
        else:
            self.stdout.write(
                self.style.WARNING("  ⚠️  No notifications found for this user")
            )


# Alternative: Simple Django shell script
"""
# Run this in Django shell: python manage.py shell

from django.contrib.auth import get_user_model
from notifications.services import NotificationService

User = get_user_model()

# Test for a specific user by email
user = User.objects.get(email="teacher@example.com")  # Change this

notification = NotificationService.send_notification(
    user=user,
    notification_type="test",
    title=f"Test for {user.role}",
    message=f"Testing notifications for {user.email}",
    link="/dashboard"
)

print(f"✅ Notification created: ID={notification.id}")
print(f"User: {user.email} ({user.role})")

# Check it was created
from notifications.models import Notification
count = Notification.objects.filter(user=user).count()
print(f"Total notifications for this user: {count}")

# Check unread count
unread = Notification.objects.filter(user=user, is_read=False).count()
print(f"Unread notifications: {unread}")
"""
