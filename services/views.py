from django.db.models import Q
from django.shortcuts import render
from .models import Service


# Create your views here.


def home(request):
    return render(request, 'home.html')


def service_list(request):
    query = request.GET.get("q", "").strip()

    # Base queryset
    services_qs = Service.objects.filter(is_active=True).select_related("category")

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

        search_results = services_qs.filter(search_filter).order_by("category__name", "price")

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
