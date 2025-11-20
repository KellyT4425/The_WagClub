
from django.urls import path
from . import views

urlpatterns = [
    path("trigger-500/", views.trigger_error),]
