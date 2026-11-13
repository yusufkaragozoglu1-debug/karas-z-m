from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from polls.models import Option, Poll, Vote

PASSWORD = "Guclu-parola-93"


def make_poll(author, closes_at=None, closed=False):
    poll = Poll.objects.create(author=author, question="Süreli soru", closes_at=closes_at, is_closed=closed)
    Option.objects.bulk_create([Option(poll=poll, text="A", order=0), Option(poll=poll, text="B", order=1)])
    return poll


class ModelTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password=PASSWORD, username="yazar")

    def test_no_deadline_is_open(self):
        poll = make_poll(self.author)
        self.assertFalse(poll.has_expired)
        self.assertFalse(poll.is_finished)

    def test_future_deadline_is_open(self):
        poll = make_poll(self.author, closes_at=timezone.now() + timedelta(hours=1))
        self.assertFalse(poll.is_finished)

    def test_past_deadline_is_finished(self):
        poll = make_poll(self.author, closes_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(poll.has_expired)
        self.assertTrue(poll.is_finished)

    def test_manual_close_is_finished_even_before_deadline(self):
        poll = make_poll(self.author, closes_at=timezone.now() + timedelta(days=1), closed=True)
        self.assertTrue(poll.is_finished)
        self.assertFalse(poll.has_expired)


class CreateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@example.com", password=PASSWORD, username="ali")
        self.client.force_login(self.user)

    def post(self, **extra):
        data = {"question": "Ne yesem?", "option_1": "A", "option_2": "B"}
        data.update(extra)
        return self.client.post(reverse("poll_create"), data)

    def test_default_is_no_deadline(self):
        self.post()
        self.assertIsNone(Poll.objects.get().closes_at)

    def test_duration_sets_closing_time(self):
        before = timezone.now()
        self.post(duration="24")
        closes_at = Poll.objects.get().closes_at
        self.assertGreaterEqual(closes_at, before + timedelta(hours=24))
        self.assertLessEqual(closes_at, timezone.now() + timedelta(hours=24))

    def test_all_offered_durations_work(self):
        for hours in ("1", "24", "72", "168"):
            Poll.objects.all().delete()
            self.post(duration=hours)
            delta = Poll.objects.get().closes_at - timezone.now()
            self.assertAlmostEqual(delta.total_seconds(), int(hours) * 3600, delta=30)

    def test_invalid_duration_rejected(self):
        response = self.post(duration="9999")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Geçerli bir süre seç.")
        self.assertEqual(Poll.objects.count(), 0)

    def test_form_shows_duration_choices(self):
        html = self.client.get(reverse("poll_create")).content.decode()
        for label in ("Süresiz", "1 saat", "24 saat", "3 gün", "7 gün"):
            self.assertIn(label, html)


class ExpiredPollBehaviourTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password=PASSWORD, username="yazar")

    def test_vote_rejected_after_deadline(self):
        poll = make_poll(self.author, closes_at=timezone.now() - timedelta(minutes=1))
        response = self.client.post(
            reverse("poll_vote", args=[poll.pk]),
            {"option": poll.options.first().pk},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Vote.objects.count(), 0)

    def test_vote_allowed_before_deadline(self):
        poll = make_poll(self.author, closes_at=timezone.now() + timedelta(hours=1))
        self.client.post(reverse("poll_vote", args=[poll.pk]), {"option": poll.options.first().pk})
        self.assertEqual(Vote.objects.count(), 1)

    def test_expired_poll_shows_results_and_no_form(self):
        poll = make_poll(self.author, closes_at=timezone.now() - timedelta(minutes=1))
        response = self.client.get(reverse("poll_detail", args=[poll.pk]))
        self.assertTrue(response.context["show_results"])
        self.assertFalse(response.context["show_form"])
        self.assertNotContains(response, "Oyumu ver")
        self.assertContains(response, "Süre doldu")
        self.assertContains(response, "Kapalı 🔒")

    def test_author_gets_no_close_button_on_expired_poll(self):
        poll = make_poll(self.author, closes_at=timezone.now() - timedelta(minutes=1))
        self.client.force_login(self.author)
        self.assertNotContains(self.client.get(reverse("poll_detail", args=[poll.pk])), "Anketi kapat")

    def test_open_poll_with_deadline_shows_countdown(self):
        poll = make_poll(self.author, closes_at=timezone.now() + timedelta(hours=5))
        response = self.client.get(reverse("poll_detail", args=[poll.pk]))
        self.assertContains(response, "Kalan süre")
        self.assertContains(response, "data-closes-at=")
        self.assertContains(response, "Oyumu ver")

    def test_poll_without_deadline_has_no_countdown(self):
        poll = make_poll(self.author)
        self.assertNotContains(self.client.get(reverse("poll_detail", args=[poll.pk])), "Kalan süre")

    def test_list_badges(self):
        make_poll(self.author, closes_at=timezone.now() + timedelta(hours=5))
        make_poll(self.author, closes_at=timezone.now() - timedelta(hours=5))
        body = self.client.get(reverse("poll_list")).content.decode()
        self.assertIn("kaldı", body)
        self.assertIn("Kapalı 🔒", body)

    def test_my_polls_marks_expired_as_closed(self):
        make_poll(self.author, closes_at=timezone.now() - timedelta(hours=1))
        self.client.force_login(self.author)
        body = self.client.get(reverse("my_polls")).content.decode()
        self.assertIn("Kapalı 🔒", body)
        self.assertNotIn("badge--open", body)
