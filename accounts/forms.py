from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Parola (tekrar)",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("username", "email")
        labels = {"username": "Kullanıcı adı", "email": "E-posta"}
        help_texts = {"username": "3–20 karakter: harf (a-z), rakam ve alt çizgi."}
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }
        error_messages = {
            "username": {"max_length": "Kullanıcı adı en fazla 20 karakter olabilir."},
            "email": {"invalid": "Geçerli bir e-posta adresi gir."},
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Bu kullanıcı adı alınmış.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta ile zaten bir hesap var.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "Parolalar eşleşmiyor.")
            else:
                candidate = User(username=cleaned.get("username", ""), email=cleaned.get("email", ""))
                try:
                    password_validation.validate_password(password2, candidate)
                except forms.ValidationError as error:
                    self.add_error("password2", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-posta",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
        error_messages={"invalid": "Geçerli bir e-posta adresi gir."},
    )
    password = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "E-posta veya parola hatalı.",
        "inactive": "E-posta veya parola hatalı.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
