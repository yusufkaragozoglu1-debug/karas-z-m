from django.shortcuts import render


def poll_list(request):
    """Temporary home page (replaced in stage 3)."""
    return render(request, "polls/list.html")


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
