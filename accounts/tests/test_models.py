from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_email_is_lowercased(self):
        user = User.objects.create_user(email="Ali@Example.COM", password="x-Strong-pass-1", username="ali")
        self.assertEqual(user.email, "ali@example.com")

    def test_username_unique_case_insensitive_in_db(self):
        User.objects.create_user(email="a@example.com", password="x-Strong-pass-1", username="Ali")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="b@example.com", password="x-Strong-pass-1", username="ali")

    def test_username_unique_case_insensitive_in_validation(self):
        User.objects.create_user(email="a@example.com", password="x-Strong-pass-1", username="Ali")
        other = User(email="b@example.com", username="ALI")
        with self.assertRaises(ValidationError) as ctx:
            other.full_clean(exclude=["password"])
        self.assertIn("username", ctx.exception.message_dict)

    def test_invalid_usernames_rejected(self):
        for bad in ["ab", "a" * 21, "ali veli", "şeyma", "ali-veli", "ali@x"]:
            with self.subTest(username=bad):
                user = User(email="t@example.com", username=bad)
                with self.assertRaises(ValidationError) as ctx:
                    user.full_clean(exclude=["password"])
                self.assertIn("username", ctx.exception.message_dict)

    def test_valid_username_accepted(self):
        user = User(email="t@example.com", username="Ali_01")
        user.full_clean(exclude=["password"])

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x", username="ali")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="Root@Example.com", password="x-Strong-pass-1", username="root")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertEqual(admin.email, "root@example.com")
