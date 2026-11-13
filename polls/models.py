from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Poll(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="polls")
    question = models.CharField("soru", max_length=200)
    description = models.CharField("açıklama", max_length=500, blank=True)
    is_closed = models.BooleanField("kapalı", default=False)
    closes_at = models.DateTimeField("kapanış zamanı", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def has_expired(self):
        return self.closes_at is not None and self.closes_at <= timezone.now()

    @property
    def is_finished(self):
        """Closed by the author or past its closing time: no more votes, results public."""
        return self.is_closed or self.has_expired

    def __str__(self):
        return self.question


class Option(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField("seçenek", max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["poll", "order"], name="polls_option_poll_order_unique"),
        ]

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="votes"
    )
    voter_token = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"],
                condition=Q(user__isnull=False),
                name="polls_vote_poll_user_unique",
            ),
            models.UniqueConstraint(
                fields=["poll", "voter_token"],
                condition=~Q(voter_token=""),
                name="polls_vote_poll_token_unique",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id} → {self.option_id}"
