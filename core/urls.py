
from django.urls import path
from . import views

urlpatterns = [
    path("trigger-500/", views.trigger_error),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]

handler404 = "core.views.custom_404"
handler500 = "core.views.custom_500"
