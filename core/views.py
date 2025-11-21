from django.shortcuts import render


def trigger_error(request):
    # Intentional error endpoint for testing monitoring/error pages.
    1 / 0
    return render(request, "500.html")


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)
