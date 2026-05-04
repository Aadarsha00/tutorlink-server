from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or repair an active admin account."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Admin email address")
        parser.add_argument(
            "--password",
            help="Admin password. If omitted, you will be prompted.",
        )
        parser.add_argument("--first-name", default="Admin")
        parser.add_argument("--last-name", default="User")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]

        if not email:
            raise CommandError("Email is required.")

        if password is None:
            password = getpass("Password: ")
            password_confirm = getpass("Password again: ")
            if password != password_confirm:
                raise CommandError("Passwords do not match.")

        if not password:
            raise CommandError("Password is required.")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": options["first_name"],
                "last_name": options["last_name"],
                "role": "admin",
            },
        )

        user.first_name = user.first_name or options["first_name"]
        user.last_name = user.last_name or options["last_name"]
        user.role = "admin"
        user.is_active = True
        user.is_email_verified = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} active admin account: {user.email}")
        )
