from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = "Guclu-parola-93"


def signup_data(**overrides):
    data = {
        "username": "ali",
        "email": "ali@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class SignupTests(TestCase):
    def test_successful_signup_logs_in_and_welcomes(self):
        response = self.client.post(reverse("signup"), signup_data(), follow=True)
        self.assertRedirects(response, reverse("poll_list"))
        self.assertContains(response, "Hoş geldin @ali! 🎉")
        self.assertContains(response, "@ali")
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get().pk)

    def test_duplicate_username_different_case(self):
        User.objects.create_user(email="x@example.com", password=PASSWORD, username="Ali")
        response = self.client.post(reverse("signup"), signup_data(username="ali"))
        self.assertContains(response, "Bu kullanıcı adı alınmış")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_different_case(self):
        User.objects.create_user(email="ali@example.com", password=PASSWORD, username="veli")
        response = self.client.post(reverse("signup"), signup_data(email="ALI@Example.com"))
        self.assertContains(response, "Bu e-posta ile zaten bir hesap var")
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch(self):
        response = self.client.post(reverse("signup"), signup_data(password2="baska-parola-12"))
        self.assertContains(response, "Parolalar eşleşmiyor")
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_rejected(self):
        response = self.client.post(reverse("signup"), signup_data(password1="123", password2="123"))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_invalid_username_rejected(self):
        response = self.client.post(reverse("signup"), signup_data(username="şeyma!"))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_email_stored_lowercase(self):
        self.client.post(reverse("signup"), signup_data(email="Ali@Example.COM"))
        self.assertEqual(User.objects.get().email, "ali@example.com")

    def test_logged_in_user_redirected_from_signup_and_login(self):
        user = User.objects.create_user(email="a@example.com", password=PASSWORD, username="ali")
        self.client.force_login(user)
        for name in ("signup", "login"):
            with self.subTest(page=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse("poll_list"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", password=PASSWORD, username="ali")

    def test_successful_login(self):
        response = self.client.post(reverse("login"), {"username": "ali@example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("poll_list"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_email_case_insensitive(self):
        response = self.client.post(reverse("login"), {"username": "ALI@Example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("poll_list"))

    def test_wrong_password_generic_error(self):
        response = self.client.post(reverse("login"), {"username": "ali@example.com", "password": "yanlis"})
        self.assertContains(response, "E-posta veya parola hatalı.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_email_same_error(self):
        response = self.client.post(reverse("login"), {"username": "yok@example.com", "password": PASSWORD})
        self.assertContains(response, "E-posta veya parola hatalı.")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_post(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("poll_list"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_redirect_after_login(self):
        response = self.client.post(
            reverse("login") + "?next=/admin/", {"username": "ali@example.com", "password": PASSWORD, "next": "/admin/"}
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def test_unsafe_next_ignored(self):
        response = self.client.post(
            reverse("login"),
            {"username": "ali@example.com", "password": PASSWORD, "next": "https://evil.example/"},
        )
        self.assertRedirects(response, reverse("poll_list"))

    def test_next_redirect_after_signup(self):
        response = self.client.post(
            reverse("signup") + "?next=/admin/",
            signup_data(username="veli", email="veli@example.com", next="/admin/"),
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)


class NavbarTests(TestCase):
    def test_visitor_sees_login_and_signup(self):
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "Giriş")
        self.assertContains(response, "Kayıt ol")
        self.assertNotContains(response, "Çıkış")

    def test_member_sees_username_and_logout_never_email(self):
        user = User.objects.create_user(email="gizli@example.com", password=PASSWORD, username="ali")
        self.client.force_login(user)
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "@ali")
        self.assertContains(response, "Çıkış")
        self.assertNotContains(response, "gizli@example.com")
