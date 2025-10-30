def cart_total(request):
    """
    Make the cart total (€) available to all templates.
    """
    cart = request.session.get("cart", {})
    total = sum(float(item["price"]) * item["quantity"]
                for item in cart.values())
    return {"cart_total": total}
