from django.urls import path
from services import views

app_name = "services"

urlpatterns = [
    path("", views.service_list, name="service_list"),
    path("reviews/<int:pk>/edit/", views.review_edit, name="review_edit"),
    path("reviews/<int:pk>/delete/", views.review_delete, name="review_delete"),
    path("<slug:slug>/", views.service_detail, name="service_detail"),
]
