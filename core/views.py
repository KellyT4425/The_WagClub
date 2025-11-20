from django.shortcuts import render

# Create your views here.


def trigger_error(request):
    1 / 0
    return render(request, "500.html")
