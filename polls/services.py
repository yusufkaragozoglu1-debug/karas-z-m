from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from .models import Option, Vote


class VoteError(Exception):
    message = "Oy verilemedi."
    status = 400

    def __str__(self):
        return self.message


class PollClosed(VoteError):
    message = "Bu anket kapandı, artık oy verilemez."
    status = 403


class InvalidOption(VoteError):
    message = "Geçerli bir seçenek seç."
    status = 400


class AlreadyVoted(VoteError):
    message = "Bu ankette zaten oy verdin."
    status = 409


def _voter_filter(user, voter_token):
    query = Q()
    if user is not None and user.is_authenticated:
        query |= Q(user=user)
    if voter_token:
        query |= Q(voter_token=voter_token)
    return query


def get_user_vote(poll, user, voter_token):
    query = _voter_filter(user, voter_token)
    if not query:
        return None
    return poll.votes.filter(query).first()


def has_voted(poll, user, voter_token):
    query = _voter_filter(user, voter_token)
    return bool(query) and poll.votes.filter(query).exists()


def voted_poll_ids(poll_ids, user, voter_token):
    """IDs (among poll_ids) this voter has voted in — a single query."""
    query = _voter_filter(user, voter_token)
    if not query or not poll_ids:
        return set()
    return set(Vote.objects.filter(query, poll_id__in=poll_ids).values_list("poll_id", flat=True))


def cast_vote(poll, option_id, user, voter_token):
    """Record a vote or raise a VoteError subclass."""
    if poll.is_finished:
        raise PollClosed()
    try:
        option_pk = int(option_id)
    except (TypeError, ValueError):
        raise InvalidOption()
    if not Option.objects.filter(pk=option_pk, poll=poll).exists():
        raise InvalidOption()
    if has_voted(poll, user, voter_token):
        raise AlreadyVoted()

    is_member = user is not None and user.is_authenticated
    if not is_member and not voter_token:
        raise InvalidOption()

    try:
        with transaction.atomic():
            return Vote.objects.create(
                poll=poll,
                option_id=option_pk,
                user=user if is_member else None,
                voter_token="" if is_member else voter_token,
            )
    except IntegrityError:
        raise AlreadyVoted()


def get_results(poll, my_option_id=None):
    """Per-option counts, rounded percentages and the leader(s), using one query."""
    options = list(poll.options.annotate(vote_count=Count("votes")).order_by("order", "id"))
    total = sum(option.vote_count for option in options)
    top = max((option.vote_count for option in options), default=0)
    results = [
        {
            "option_id": option.pk,
            "text": option.text,
            "order": option.order,
            "votes": option.vote_count,
            "percent": int(option.vote_count * 100 / total + 0.5) if total else 0,
            "is_leading": top > 0 and option.vote_count == top,
            "is_mine": option.pk == my_option_id,
        }
        for option in options
    ]
    return {"total_votes": total, "results": results}
