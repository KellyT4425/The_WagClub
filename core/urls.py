
from django.urls import path
from . import views

urlpatterns = [
    path("trigger-500/", views.trigger_error),
]

handler404 = "core.views.custom_404"
handler500 = "core.views.custom_500"
