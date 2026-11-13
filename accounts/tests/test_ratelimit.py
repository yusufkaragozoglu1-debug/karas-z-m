from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from config import ratelimit
from polls.models import Option, Poll

PASSWORD = "Guclu-parola-93"


@override_settings(RATELIMIT_ENABLED=True)
class RateLimitTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)


class LimiterUnitTests(RateLimitTestCase):
    def test_allows_up_to_limit_then_blocks(self):
        results = [ratelimit.is_limited("k", limit=3, window=60) for _ in range(5)]
        self.assertEqual(results, [False, False, False, True, True])

    def test_keys_are_independent(self):
        for _ in range(4):
            ratelimit.is_limited("a", limit=3, window=60)
        self.assertFalse(ratelimit.is_limited("b", limit=3, window=60))

    def test_window_expiry_resets_counter(self):
        with mock.patch("config.ratelimit.time.time", return_value=1000.0):
            for _ in range(4):
                ratelimit.is_limited("k", limit=3, window=60)
        with mock.patch("config.ratelimit.time.time", return_value=1061.0):
            self.assertFalse(ratelimit.is_limited("k", limit=3, window=60))

    def test_fails_open_when_cache_is_broken(self):
        with mock.patch("config.ratelimit.cache.get", side_effect=RuntimeError("db down")):
            self.assertFalse(ratelimit.is_limited("k", limit=0, window=60))

    def test_client_ip_prefers_forwarded_header(self):
        request = mock.Mock(META={"HTTP_X_FORWARDED_FOR": "1.2.3.4, 10.0.0.1", "REMOTE_ADDR": "10.0.0.1"})
        self.assertEqual(ratelimit.client_ip(request), "1.2.3.4")
        request = mock.Mock(META={"REMOTE_ADDR": "9.9.9.9"})
        self.assertEqual(ratelimit.client_ip(request), "9.9.9.9")


class ViewLimitTests(RateLimitTestCase):
    def test_login_blocked_after_10_attempts(self):
        data = {"username": "yok@example.com", "password": "yanlis"}
        for _ in range(10):
            self.assertEqual(self.client.post(reverse("login"), data).status_code, 200)
        response = self.client.post(reverse("login"), data)
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Biraz yavaşla", status_code=429)
        self.assertEqual(response["Retry-After"], "60")

    def test_login_get_is_not_limited(self):
        for _ in range(15):
            self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_signup_blocked_after_5_attempts(self):
        data = {"username": "ab", "email": "x", "password1": "a", "password2": "b"}
        for _ in range(5):
            self.assertEqual(self.client.post(reverse("signup"), data).status_code, 200)
        self.assertEqual(self.client.post(reverse("signup"), data).status_code, 429)

    def test_limit_is_per_ip(self):
        data = {"username": "yok@example.com", "password": "yanlis"}
        for _ in range(11):
            self.client.post(reverse("login"), data, REMOTE_ADDR="5.5.5.5")
        response = self.client.post(reverse("login"), data, REMOTE_ADDR="6.6.6.6")
        self.assertEqual(response.status_code, 200)

    def test_poll_create_limited_per_user(self):
        user = User.objects.create_user(email="a@example.com", password=PASSWORD, username="ali")
        self.client.force_login(user)
        data = {"question": "Soru", "option_1": "A", "option_2": "B"}
        for _ in range(10):
            self.assertEqual(self.client.post(reverse("poll_create"), data).status_code, 302)
        self.assertEqual(self.client.post(reverse("poll_create"), data).status_code, 429)
        self.assertEqual(Poll.objects.count(), 10)

    def test_vote_returns_json_429(self):
        author = User.objects.create_user(email="a@example.com", password=PASSWORD, username="ali")
        poll = Poll.objects.create(author=author, question="Soru")
        option = Option.objects.create(poll=poll, text="A", order=0)
        Option.objects.create(poll=poll, text="B", order=1)
        url = reverse("poll_vote", args=[poll.pk])
        for _ in range(60):
            self.client.post(url, {"option": option.pk}, headers={"Accept": "application/json"})
        response = self.client.post(url, {"option": option.pk}, headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()["ok"])


class HoneypotTests(RateLimitTestCase):
    def data(self, **extra):
        data = {"username": "ali", "email": "ali@example.com", "password1": PASSWORD, "password2": PASSWORD}
        data.update(extra)
        return data

    def test_filled_honeypot_rejects_signup(self):
        response = self.client.post(reverse("signup"), self.data(website="http://spam.example"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_empty_honeypot_allows_signup(self):
        self.client.post(reverse("signup"), self.data(website=""))
        self.assertEqual(User.objects.count(), 1)

    def test_honeypot_is_hidden_from_people(self):
        html = self.client.get(reverse("signup")).content.decode()
        self.assertIn('class="hp"', html)
        self.assertIn('aria-hidden="true"', html)
        self.assertIn('tabindex="-1"', html)
