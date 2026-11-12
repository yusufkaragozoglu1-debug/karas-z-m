from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from accounts.models import User
from polls.models import Option, Poll, Vote

PASSWORD = "Guclu-parola-93"


def make_poll(author, question="Pizza mı, hamburger mi?", options=("Pizza", "Hamburger")):
    poll = Poll.objects.create(author=author, question=question)
    Option.objects.bulk_create([Option(poll=poll, text=t, order=i) for i, t in enumerate(options)])
    return poll


def create_data(**overrides):
    data = {"question": "Ne yesem?", "description": "", "option_1": "Pizza", "option_2": "Döner"}
    data.update(overrides)
    return data


class PollCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", password=PASSWORD, username="ali")

    def test_visitor_redirected_to_login_with_next(self):
        response = self.client.get(reverse("poll_create"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('poll_create')}")

    def test_visitor_post_does_not_create(self):
        self.client.post(reverse("poll_create"), create_data())
        self.assertEqual(Poll.objects.count(), 0)

    def test_successful_creation(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("poll_create"),
            create_data(option_3="Lahmacun", option_4="  Kebap  ", option_5="Çorba", description="  Aç  "),
            follow=True,
        )
        poll = Poll.objects.get()
        self.assertRedirects(response, reverse("poll_detail", args=[poll.pk]))
        self.assertContains(response, "Anketin yayında! 🎉")
        self.assertEqual(poll.author, self.user)
        self.assertEqual(poll.description, "Aç")
        self.assertEqual(
            list(poll.options.values_list("text", "order")),
            [("Pizza", 0), ("Döner", 1), ("Lahmacun", 2), ("Kebap", 3), ("Çorba", 4)],
        )

    def test_single_option_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("poll_create"), create_data(option_2=""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Poll.objects.count(), 0)
        self.assertContains(response, "Bu seçenek zorunlu.")

    def test_whitespace_only_option_rejected(self):
        self.client.force_login(self.user)
        self.client.post(reverse("poll_create"), create_data(option_2="   "))
        self.assertEqual(Poll.objects.count(), 0)

    def test_duplicate_options_rejected_case_insensitive(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("poll_create"), create_data(option_2="PİZZA".replace("İ", "i")))
        self.assertContains(response, "Aynı seçeneği iki kez yazamazsın.")
        self.assertEqual(Poll.objects.count(), 0)

    def test_sixth_option_not_accepted(self):
        self.client.force_login(self.user)
        data = create_data(option_3="C", option_4="D", option_5="E", option_6="F")
        self.client.post(reverse("poll_create"), data)
        self.assertEqual(Option.objects.count(), 5)

    def test_gaps_are_compacted(self):
        self.client.force_login(self.user)
        self.client.post(reverse("poll_create"), create_data(option_3="", option_4="Kebap"))
        self.assertEqual(list(Option.objects.values_list("text", "order")), [("Pizza", 0), ("Döner", 1), ("Kebap", 2)])

    def test_length_limits(self):
        self.client.force_login(self.user)
        self.client.post(reverse("poll_create"), create_data(question="x" * 201))
        self.client.post(reverse("poll_create"), create_data(option_1="x" * 81))
        self.client.post(reverse("poll_create"), create_data(description="x" * 501))
        self.assertEqual(Poll.objects.count(), 0)

    def test_failed_creation_leaves_no_poll_behind(self):
        self.client.force_login(self.user)
        self.client.post(reverse("poll_create"), create_data(option_1="A", option_2="a"))
        self.assertEqual(Poll.objects.count(), 0)
        self.assertEqual(Option.objects.count(), 0)


class PollListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ali@example.com", password=PASSWORD, username="ali")

    def test_newest_first(self):
        first = make_poll(self.user, "Eski")
        second = make_poll(self.user, "Yeni")
        response = self.client.get(reverse("poll_list"))
        self.assertEqual([p.pk for p in response.context["page"]], [second.pk, first.pk])

    def test_pagination_ten_per_page(self):
        for i in range(12):
            make_poll(self.user, f"Soru {i}")
        self.assertEqual(len(self.client.get(reverse("poll_list")).context["page"]), 10)
        self.assertEqual(len(self.client.get(reverse("poll_list") + "?sayfa=2").context["page"]), 2)

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse("poll_list")), "Henüz anket yok")

    def test_card_shows_counts_and_username_not_email(self):
        poll = make_poll(self.user)
        Vote.objects.create(poll=poll, option=poll.options.first(), user=self.user)
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "@ali")
        self.assertContains(response, "2 seçenek")
        self.assertContains(response, "1 oy")
        self.assertNotContains(response, "ali@example.com")

    def test_query_count_does_not_grow_with_polls(self):
        make_poll(self.user)
        with CaptureQueriesContext(connection) as few:
            self.client.get(reverse("poll_list"))
        for i in range(8):
            make_poll(self.user, f"Soru {i}")
        with CaptureQueriesContext(connection) as many:
            self.client.get(reverse("poll_list"))
        self.assertEqual(len(few), len(many))


class PollDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="gizli@example.com", password=PASSWORD, username="ali")
        self.poll = make_poll(self.user, options=("A", "B", "C"))

    def test_detail_shows_author_username_not_email(self):
        response = self.client.get(reverse("poll_detail", args=[self.poll.pk]))
        self.assertContains(response, "@ali")
        self.assertNotContains(response, "gizli@example.com")

    def test_options_listed_in_order_with_color_classes(self):
        response = self.client.get(reverse("poll_detail", args=[self.poll.pk]))
        self.assertContains(response, "option--1")
        self.assertContains(response, "option--3")
        self.assertNotContains(response, "option--4")
        self.assertEqual([o.text for o in response.context["options"]], ["A", "B", "C"])

    def test_missing_poll_404(self):
        self.assertEqual(self.client.get(reverse("poll_detail", args=[9999])).status_code, 404)


class VoteConstraintTests(TestCase):
    def test_unique_constraints(self):
        user = User.objects.create_user(email="a@example.com", password=PASSWORD, username="ali")
        poll = make_poll(user)
        option = poll.options.first()
        Vote.objects.create(poll=poll, option=option, user=user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=poll, option=option, user=user)
        Vote.objects.create(poll=poll, option=option, voter_token="t1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vote.objects.create(poll=poll, option=option, voter_token="t1")
        # Many anonymous-token-less rows with null user are not blocked by the constraints' conditions.
        Vote.objects.create(poll=poll, option=option, voter_token="t2")
