from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

username_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_]{3,20}$",
    message="Kullanıcı adı 3–20 karakter olmalı; sadece harf (a-z), rakam ve alt çizgi içerebilir.",
)


class CustomUserManager(UserManager):
    def _create_user_object(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("E-posta zorunludur.")
        email = self.normalize_email(email).lower()
        return super()._create_user_object(username, email, password, **extra_fields)

    def create_user(self, email=None, password=None, username=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, username=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser is_staff=True olmalı.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser is_superuser=True olmalı.")
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(
        "kullanıcı adı",
        max_length=20,
        validators=[username_validator],
        help_text="3–20 karakter: harf, rakam ve alt çizgi.",
    )
    email = models.EmailField("e-posta", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique"),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        if exclude and "username" in exclude:
            return
        from django.core.exceptions import ValidationError

        clash = User.objects.filter(username__iexact=self.username).exclude(pk=self.pk)
        if clash.exists():
            raise ValidationError({"username": "Bu kullanıcı adı alınmış."})

    def __str__(self):
        return self.username
