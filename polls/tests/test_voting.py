import json

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from polls import services, voter
from polls.models import Option, Poll, Vote

PASSWORD = "Guclu-parola-93"


def make_poll(author, question="Pizza mı, hamburger mi?", options=("Pizza", "Hamburger"), closed=False):
    poll = Poll.objects.create(author=author, question=question, is_closed=closed)
    Option.objects.bulk_create([Option(poll=poll, text=t, order=i) for i, t in enumerate(options)])
    return poll


def make_user(name="ali"):
    return User.objects.create_user(email=f"{name}@example.com", password=PASSWORD, username=name)


class BaseVotingTest(TestCase):
    def setUp(self):
        self.author = make_user("yazar")
        self.poll = make_poll(self.author, options=("A", "B", "C"))
        self.a, self.b, self.c = self.poll.options.all()
        self.vote_url = reverse("poll_vote", args=[self.poll.pk])
        self.detail_url = reverse("poll_detail", args=[self.poll.pk])


class VisitorVoteTests(BaseVotingTest):
    def test_visitor_can_vote_and_gets_cookie(self):
        response = self.client.post(self.vote_url, {"option": self.a.pk}, follow=True)
        self.assertRedirects(response, self.detail_url)
        self.assertContains(response, "Oyun kaydedildi! 🙌")
        self.assertIn(voter.COOKIE_NAME, self.client.cookies)
        cookie = self.client.cookies[voter.COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(Vote.objects.get().option, self.a)

    def test_second_vote_with_same_cookie_rejected(self):
        self.client.post(self.vote_url, {"option": self.a.pk})
        response = self.client.post(self.vote_url, {"option": self.b.pk}, follow=True)
        self.assertContains(response, "zaten oy verdin")
        self.assertEqual(Vote.objects.count(), 1)

    def test_new_browser_without_cookie_can_vote_again(self):
        self.client.post(self.vote_url, {"option": self.a.pk})
        Client().post(self.vote_url, {"option": self.a.pk})
        self.assertEqual(Vote.objects.count(), 2)

    def test_tampered_cookie_is_ignored(self):
        self.client.cookies[voter.COOKIE_NAME] = "a" * 32
        self.client.post(self.vote_url, {"option": self.a.pk})
        vote = Vote.objects.get()
        self.assertNotEqual(vote.voter_token, "a" * 32)

    def test_get_cannot_vote(self):
        response = self.client.get(self.vote_url, {"option": self.a.pk})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Vote.objects.count(), 0)

    def test_option_from_other_poll_rejected(self):
        other = make_poll(self.author, "Başka", options=("X", "Y"))
        response = self.client.post(self.vote_url, {"option": other.options.first().pk}, follow=True)
        self.assertContains(response, "Geçerli bir seçenek seç.")
        self.assertEqual(Vote.objects.count(), 0)

    def test_missing_or_garbage_option_rejected(self):
        for value in (None, "", "abc"):
            with self.subTest(value=value):
                data = {} if value is None else {"option": value}
                self.client.post(self.vote_url, data)
        self.assertEqual(Vote.objects.count(), 0)

    def test_closed_poll_rejects_votes(self):
        self.poll.is_closed = True
        self.poll.save()
        response = self.client.post(self.vote_url, {"option": self.a.pk}, follow=True)
        self.assertContains(response, "Bu anket kapandı")
        self.assertEqual(Vote.objects.count(), 0)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.vote_url, {"option": self.a.pk})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Vote.objects.count(), 0)


class MemberVoteTests(BaseVotingTest):
    def setUp(self):
        super().setUp()
        self.user = make_user("ali")
        self.client.force_login(self.user)

    def test_member_vote_stored_with_user(self):
        self.client.post(self.vote_url, {"option": self.b.pk})
        vote = Vote.objects.get()
        self.assertEqual((vote.user, vote.voter_token), (self.user, ""))
        self.assertNotIn(voter.COOKIE_NAME, self.client.cookies)

    def test_member_cannot_vote_twice(self):
        self.client.post(self.vote_url, {"option": self.a.pk})
        self.client.post(self.vote_url, {"option": self.b.pk})
        self.assertEqual(Vote.objects.count(), 1)

    def test_visitor_vote_then_login_cannot_vote_again(self):
        anon = Client()
        anon.post(self.vote_url, {"option": self.a.pk})
        anon.force_login(self.user)
        anon.post(self.vote_url, {"option": self.b.pk})
        self.assertEqual(Vote.objects.count(), 1)


class ResultsVisibilityTests(BaseVotingTest):
    def test_results_hidden_before_voting(self):
        response = self.client.get(self.detail_url)
        self.assertFalse(response.context["show_results"])
        self.assertContains(response, "Oyumu ver")
        self.assertNotContains(response, "Toplam")

    def test_results_visible_after_voting(self):
        self.client.post(self.vote_url, {"option": self.a.pk})
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["show_results"])
        self.assertContains(response, "Senin seçimin ✓")
        self.assertContains(response, "👑 Önde")
        self.assertNotContains(response, "Oyumu ver")

    def test_author_always_sees_results(self):
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["show_results"])
        self.assertContains(response, "Henüz oy yok")

    def test_closed_poll_results_public(self):
        self.poll.is_closed = True
        self.poll.save()
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["show_results"])
        self.assertNotContains(response, "Oyumu ver")

    def test_other_member_does_not_see_owner_buttons(self):
        self.client.force_login(make_user("ali"))
        self.assertNotContains(self.client.get(self.detail_url), "Anketi kapat")

    def test_author_sees_owner_buttons(self):
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Anketi kapat")
        self.assertContains(response, "Sil")


class ResultsCalculationTests(TestCase):
    def test_percentages_round_and_leaders(self):
        author = make_user("yazar")
        poll = make_poll(author, options=("A", "B", "C"))
        a, b, c = poll.options.all()
        for i, option in enumerate([a, a, b]):
            Vote.objects.create(poll=poll, option=option, voter_token=f"t{i}")
        data = services.get_results(poll)
        self.assertEqual(data["total_votes"], 3)
        self.assertEqual([r["percent"] for r in data["results"]], [67, 33, 0])
        self.assertEqual([r["is_leading"] for r in data["results"]], [True, False, False])

    def test_tie_marks_all_leaders(self):
        author = make_user("yazar")
        poll = make_poll(author, options=("A", "B", "C"))
        a, b, c = poll.options.all()
        Vote.objects.create(poll=poll, option=a, voter_token="t1")
        Vote.objects.create(poll=poll, option=b, voter_token="t2")
        data = services.get_results(poll)
        self.assertEqual([r["is_leading"] for r in data["results"]], [True, True, False])

    def test_no_votes_no_leader(self):
        poll = make_poll(make_user("yazar"))
        data = services.get_results(poll)
        self.assertEqual(data["total_votes"], 0)
        self.assertFalse(any(r["is_leading"] for r in data["results"]))
        self.assertEqual([r["percent"] for r in data["results"]], [0, 0])

    def test_results_use_single_query(self):
        poll = make_poll(make_user("yazar"), options=("A", "B", "C", "D", "E"))
        with CaptureQueriesContext(connection) as queries:
            services.get_results(poll)
        self.assertEqual(len(queries), 1)


class JsonVoteTests(BaseVotingTest):
    def post_json(self, client, option):
        return client.post(self.vote_url, {"option": option}, headers={"Accept": "application/json"})

    def test_success_payload(self):
        response = self.post_json(self.client, self.a.pk)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["total_votes"], 1)
        self.assertEqual(
            set(data["results"][0]),
            {"option_id", "text", "order", "votes", "percent", "is_leading", "is_mine"},
        )
        self.assertTrue(data["results"][0]["is_mine"])
        self.assertEqual(data["results"][0]["percent"], 100)

    def test_error_codes(self):
        self.assertEqual(self.post_json(self.client, 99999).status_code, 400)
        self.post_json(self.client, self.a.pk)
        self.assertEqual(self.post_json(self.client, self.b.pk).status_code, 409)
        self.poll.is_closed = True
        self.poll.save()
        self.assertEqual(self.post_json(Client(), self.a.pk).status_code, 403)

    def test_error_body_is_json(self):
        response = self.post_json(self.client, 99999)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertTrue(data["message"])

    def test_json_never_contains_email(self):
        member = make_user("ali")
        client = Client()
        client.force_login(member)
        response = self.post_json(client, self.a.pk)
        self.assertNotIn("@example.com", response.content.decode())
        self.assertNotIn("email", response.content.decode())


class CloseDeleteTests(BaseVotingTest):
    def test_author_can_close(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse("poll_close", args=[self.poll.pk]))
        self.assertRedirects(response, self.detail_url)
        self.poll.refresh_from_db()
        self.assertTrue(self.poll.is_closed)

    def test_non_author_cannot_close_or_delete(self):
        self.client.force_login(make_user("ali"))
        self.assertEqual(self.client.post(reverse("poll_close", args=[self.poll.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("poll_delete", args=[self.poll.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("poll_delete", args=[self.poll.pk])).status_code, 404)
        self.poll.refresh_from_db()
        self.assertFalse(self.poll.is_closed)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_close_requires_post(self):
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(reverse("poll_close", args=[self.poll.pk])).status_code, 405)

    def test_delete_confirm_then_post(self):
        self.client.force_login(self.author)
        url = reverse("poll_delete", args=[self.poll.pk])
        self.assertContains(self.client.get(url), "Evet, sil")
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())
        response = self.client.post(url)
        self.assertRedirects(response, reverse("my_polls"))
        self.assertFalse(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_visitor_redirected_to_login(self):
        response = self.client.post(reverse("poll_close", args=[self.poll.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class MyPollsAndBadgesTests(BaseVotingTest):
    def test_my_polls_requires_login(self):
        self.assertEqual(self.client.get(reverse("my_polls")).status_code, 302)

    def test_my_polls_lists_only_own_with_status(self):
        make_poll(self.author, "Kapalı soru", closed=True)
        other = make_user("ali")
        make_poll(other, "Başkasının sorusu")
        self.client.force_login(self.author)
        response = self.client.get(reverse("my_polls"))
        self.assertContains(response, "Kapalı soru")
        self.assertContains(response, "Kapalı 🔒")
        self.assertContains(response, "Açık")
        self.assertNotContains(response, "Başkasının sorusu")

    def test_my_polls_total_votes(self):
        Vote.objects.create(poll=self.poll, option=self.a, voter_token="t1")
        Vote.objects.create(poll=self.poll, option=self.b, voter_token="t2")
        self.client.force_login(self.author)
        self.assertContains(self.client.get(reverse("my_polls")), "2 oy")

    def test_list_badges(self):
        closed = make_poll(self.author, "Kapalı olan", closed=True)
        self.client.post(self.vote_url, {"option": self.a.pk})
        response = self.client.get(reverse("poll_list"))
        self.assertContains(response, "Oy verdin ✓")
        self.assertContains(response, "Kapalı 🔒")
        by_pk = {p.pk: p for p in response.context["polls"]}
        self.assertTrue(by_pk[self.poll.pk].has_voted)
        self.assertFalse(by_pk[closed.pk].has_voted)

    def test_list_query_count_constant_with_votes(self):
        user = make_user("ali")
        self.client.force_login(user)
        with CaptureQueriesContext(connection) as few:
            self.client.get(reverse("poll_list"))
        for i in range(8):
            poll = make_poll(self.author, f"Soru {i}")
            Vote.objects.create(poll=poll, option=poll.options.first(), user=user)
        with CaptureQueriesContext(connection) as many:
            self.client.get(reverse("poll_list"))
        self.assertEqual(len(few), len(many))

    def test_my_polls_query_count_constant(self):
        self.client.force_login(self.author)
        with CaptureQueriesContext(connection) as few:
            self.client.get(reverse("my_polls"))
        for i in range(8):
            make_poll(self.author, f"Soru {i}")
        with CaptureQueriesContext(connection) as many:
            self.client.get(reverse("my_polls"))
        self.assertEqual(len(few), len(many))


class AuthorVotingTests(BaseVotingTest):
    def test_author_sees_results_and_vote_form(self):
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertTrue(response.context["show_results"])
        self.assertTrue(response.context["show_form"])
        self.assertContains(response, "Henüz oy yok")
        self.assertContains(response, "Oyumu ver")
        self.assertContains(response, "Sen de oy ver")

    def test_author_can_vote_once_and_form_disappears(self):
        self.client.force_login(self.author)
        self.client.post(self.vote_url, {"option": self.a.pk})
        self.assertEqual(Vote.objects.get().user, self.author)
        response = self.client.get(self.detail_url)
        self.assertFalse(response.context["show_form"])
        self.assertContains(response, "Senin seçimin ✓")
        self.assertNotContains(response, "Oyumu ver")
        self.client.post(self.vote_url, {"option": self.b.pk})
        self.assertEqual(Vote.objects.count(), 1)

    def test_author_cannot_vote_in_closed_poll(self):
        self.poll.is_closed = True
        self.poll.save()
        self.client.force_login(self.author)
        self.assertFalse(self.client.get(self.detail_url).context["show_form"])
        self.client.post(self.vote_url, {"option": self.a.pk})
        self.assertEqual(Vote.objects.count(), 0)

    def test_visitor_view_unchanged(self):
        response = self.client.get(self.detail_url)
        self.assertFalse(response.context["show_results"])
        self.assertTrue(response.context["show_form"])
        self.assertNotContains(response, "Sen de oy ver")
