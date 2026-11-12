"""Regression tests from the stage 7 review: performance, privacy, state-changing requests."""

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from polls.models import Option, Poll, Vote

PASSWORD = "Guclu-parola-93"


def make_poll(author, question="Soru", n_options=3):
    poll = Poll.objects.create(author=author, question=question)
    Option.objects.bulk_create([Option(poll=poll, text=f"S{i}", order=i) for i in range(n_options)])
    return poll


class DetailQueryCountTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password=PASSWORD, username="yazar")

    def count_queries(self, client, url):
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx)

    def test_voting_form_query_count_independent_of_option_count(self):
        small = make_poll(self.author, n_options=2)
        large = make_poll(self.author, n_options=5)
        self.assertEqual(
            self.count_queries(self.client, reverse("poll_detail", args=[small.pk])),
            self.count_queries(self.client, reverse("poll_detail", args=[large.pk])),
        )

    def test_results_query_count_independent_of_vote_count(self):
        poll = make_poll(self.author, n_options=5)
        self.client.force_login(self.author)
        url = reverse("poll_detail", args=[poll.pk])
        before = self.count_queries(self.client, url)
        options = list(poll.options.all())
        Vote.objects.bulk_create(
            [Vote(poll=poll, option=options[i % 5], voter_token=f"t{i}") for i in range(40)]
        )
        self.assertEqual(before, self.count_queries(self.client, url))


class PrivacyTests(TestCase):
    def test_no_email_on_any_public_page(self):
        author = User.objects.create_user(email="gizli.yazar@example.com", password=PASSWORD, username="yazar")
        voter = User.objects.create_user(email="gizli.oycu@example.com", password=PASSWORD, username="oycu")
        poll = make_poll(author)
        Vote.objects.create(poll=poll, option=poll.options.first(), user=voter)
        pages = [reverse("poll_list"), reverse("poll_detail", args=[poll.pk])]
        for who in (None, author, voter):
            client = Client()
            if who:
                client.force_login(who)
            pages_for_user = pages + ([reverse("my_polls")] if who else [])
            for url in pages_for_user:
                with self.subTest(user=getattr(who, "username", "ziyaretci"), url=url):
                    body = client.get(url).content.decode()
                    self.assertNotIn("@example.com", body)


class StateChangingRequestTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email="a@example.com", password=PASSWORD, username="yazar")
        self.poll = make_poll(self.author)

    def test_get_never_changes_state(self):
        self.client.force_login(self.author)
        for name in ("poll_vote", "poll_close"):
            response = self.client.get(reverse(name, args=[self.poll.pk]))
            self.assertEqual(response.status_code, 405, name)
        # The delete URL answers GET with a confirmation page only.
        self.assertEqual(self.client.get(reverse("poll_delete", args=[self.poll.pk])).status_code, 200)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk, is_closed=False).exists())

    def test_post_endpoints_enforce_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.author)
        for name in ("poll_close", "poll_delete", "poll_vote"):
            response = client.post(reverse(name, args=[self.poll.pk]))
            self.assertEqual(response.status_code, 403, name)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk, is_closed=False).exists())

    def test_user_content_is_escaped(self):
        poll = make_poll(self.author, question="<script>alert(1)</script>")
        body = self.client.get(reverse("poll_detail", args=[poll.pk])).content.decode()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;", body)
