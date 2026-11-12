from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PollCreateForm
from .models import Poll

PAGE_SIZE = 10


def poll_list(request):
    polls = (
        Poll.objects.select_related("author")
        .annotate(
            total_votes=Count("votes", distinct=True),
            option_count=Count("options", distinct=True),
        )
        .order_by("-created_at", "-id")
    )
    page = Paginator(polls, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    return render(request, "polls/list.html", {"page": page})


def poll_detail(request, pk):
    poll = get_object_or_404(Poll.objects.select_related("author").prefetch_related("options"), pk=pk)
    return render(request, "polls/detail.html", {"poll": poll, "options": poll.options.all()})


@login_required
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


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
