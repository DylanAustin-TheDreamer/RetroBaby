from .models import BasketItem


def basket_context(request):
    session_id = request.session.session_key
    basket_count = 0
    if session_id:
        basket_count = BasketItem.objects.filter(session_id=session_id).count()
    return {'basket_count': basket_count}
