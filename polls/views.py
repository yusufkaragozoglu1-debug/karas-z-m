from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.ratelimit import rate_limit

from . import services, voter
from .forms import PollCreateForm
from .models import Poll

PAGE_SIZE = 10


def _annotated_polls():
    return Poll.objects.select_related("author").annotate(
        total_votes=Count("votes", distinct=True),
        option_count=Count("options", distinct=True),
    )


def poll_list(request):
    polls = _annotated_polls().order_by("-created_at", "-id")
    page = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    page_polls = list(page.object_list)
    voted = services.voted_poll_ids(
        [poll.pk for poll in page_polls], request.user, voter.get_voter_token(request)
    )
    for poll in page_polls:
        poll.has_voted = poll.pk in voted
    return render(request, "polls/list.html", {"page": page, "polls": page_polls})


def poll_detail(request, pk):
    poll = get_object_or_404(Poll.objects.select_related("author"), pk=pk)
    token = voter.get_voter_token(request)
    is_author = request.user.is_authenticated and poll.author_id == request.user.pk
    my_vote = services.get_user_vote(poll, request.user, token)
    show_results = is_author or poll.is_closed or my_vote is not None

    context = {"poll": poll, "is_author": is_author, "show_results": show_results, "my_vote": my_vote}
    if show_results:
        context.update(services.get_results(poll, my_option_id=my_vote.option_id if my_vote else None))
    else:
        context["options"] = poll.options.all()
    return render(request, "polls/detail.html", context)


@login_required
@rate_limit("poll_create", limit=10, window=3600, by="user")
def poll_create(request):
    if request.method == "POST":
        form = PollCreateForm(request.POST)
        if form.is_valid():
            poll = form.save(author=request.user)
            messages.success(request, "Anketin yayında! 🎉")
            return redirect("poll_detail", pk=poll.pk)
    else:
        form = PollCreateForm()
    return render(request, "polls/create.html", {"form": form})


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


@require_POST
@rate_limit("vote", limit=60, window=600)
def poll_vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    token = voter.get_voter_token(request)
    issue_cookie = False
    if not request.user.is_authenticated and not token:
        token = voter.new_voter_token()
        issue_cookie = True

    try:
        vote = services.cast_vote(poll, request.POST.get("option"), request.user, token)
    except services.VoteError as error:
        if _wants_json(request):
            return JsonResponse({"ok": False, "message": error.message}, status=error.status)
        messages.error(request, error.message)
        return redirect("poll_detail", pk=poll.pk)

    message = "Oyun kaydedildi! 🙌"
    if _wants_json(request):
        data = services.get_results(poll, my_option_id=vote.option_id)
        response = JsonResponse({"ok": True, "message": message, **data})
    else:
        messages.success(request, message)
        response = redirect("poll_detail", pk=poll.pk)
    if issue_cookie:
        voter.set_voter_cookie(response, token)
    return response


@login_required
@require_POST
def poll_close(request, pk):
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    if not poll.is_closed:
        poll.is_closed = True
        poll.save(update_fields=["is_closed"])
    messages.success(request, "Anket kapatıldı. 🔒")
    return redirect("poll_detail", pk=poll.pk)


@login_required
def poll_delete(request, pk):
    poll = get_object_or_404(Poll, pk=pk, author=request.user)
    if request.method == "POST":
        poll.delete()
        messages.success(request, "Anket silindi.")
        return redirect("my_polls")
    return render(request, "polls/confirm_delete.html", {"poll": poll})


@login_required
def my_polls(request):
    polls = _annotated_polls().filter(author=request.user).order_by("-created_at", "-id")
    return render(request, "polls/my_polls.html", {"polls": polls})


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
