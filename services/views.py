"""Service catalogue views: home, listing with search, and detail pages."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from .models import Service, Review
from .forms import ReviewForm
from orders.models import Voucher


def home(request):
    """Homepage view."""
    return render(request, 'home.html')


def service_list(request):
    """List services by category with optional search filtering."""
    query = (
        request.GET.get("q")
        or request.GET.get("query")
        or request.GET.get("search")
        or ""
    ).strip()

    # Base queryset
    services_qs = Service.objects.filter(is_active=True).select_related(
        "category"
    )

    search_results = []

    if query:
        # Loosen search to catch stems (e.g., "grooming" -> "groom")
        terms = set()
        for part in query.split():
            terms.add(part)
            if part.endswith("ing") and len(part) > 4:
                terms.add(part[:-3])
            if part.endswith("es") and len(part) > 3:
                terms.add(part[:-2])
            if part.endswith("s") and len(part) > 3:
                terms.add(part[:-1])
        terms.add(query)
        terms = [t for t in terms if t]

        search_filter = Q()
        for term in terms:
            search_filter |= (
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(category__name__icontains=term)
            )

        search_results = services_qs.filter(search_filter).order_by(
            "category__name", "price"
        )

    # Always show full categories, even when searching
    passes = services_qs.filter(category__name="Passes").order_by("price")
    packages = services_qs.filter(category__name="Packages").order_by("price")
    offers = services_qs.filter(category__name="Offers").order_by("price")

    context = {
        "doggy_daycare_pass": passes,
        "doggy_grooming_packs": packages,
        "pet_offers": offers,
        "search_query": query,
        "search_results": search_results,
    }

    return render(request, "services/service_list.html", context)


def service_detail(request, slug):
    """Display details for a single service."""
    service = get_object_or_404(
        Service.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )
    reviews = service.reviews.select_related("user")
    rating_stats = service.reviews.aggregate(
        average=Avg("rating"), count=Count("id")
    )

    user_can_review = False
    if request.user.is_authenticated:
        # Require a voucher purchase before allowing a review.
        user_can_review = Voucher.objects.filter(
            user=request.user, service=service
        ).exists()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.warning(request, "Log in to leave a review.")
            return redirect("account_login")
        if not user_can_review:
            messages.warning(
                request, "You need to purchase this service before reviewing."
            )
            return redirect("services:service_detail", slug=service.slug)
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.service = service
            review.user = request.user
            review.save()
            messages.success(request, "Review submitted.")
            return redirect("services:service_detail", slug=service.slug)
    else:
        form = ReviewForm()

    context = {
        "service": service,
        "reviews": reviews,
        "rating_stats": rating_stats,
        "form": form,
        "user_can_review": user_can_review,
    }
    return render(request, "services/service_detail.html", context)


@login_required
def review_edit(request, pk):
    """Allow review author to edit their review."""
    review = get_object_or_404(Review.objects.select_related("service", "user"), pk=pk)
    if review.user_id != request.user.id:
        return HttpResponseForbidden("You do not own this review.")
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated.")
            return redirect("services:service_detail", slug=review.service.slug)
    else:
        form = ReviewForm(instance=review)
    return render(
        request,
        "services/review_form.html",
        {"form": form, "review": review, "mode": "edit"},
    )


@login_required
def review_delete(request, pk):
    """Allow review author to delete their review."""
    review = get_object_or_404(Review.objects.select_related("service", "user"), pk=pk)
    if review.user_id != request.user.id:
        return HttpResponseForbidden("You do not own this review.")
    if request.method == "POST":
        slug = review.service.slug
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect("services:service_detail", slug=slug)
    return render(
        request,
        "services/review_confirm_delete.html",
        {"review": review},
    )
