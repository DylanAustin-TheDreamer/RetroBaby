from multiprocessing import context
from django.http import JsonResponse
from django.shortcuts import redirect, render
import requests
from urllib3 import request
from .models import Contacts, BasketItem, OrderItem, Orders
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from CardMain import models


PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"


#for testing email page
def test_email_view(request):
    return render(request, 'cardMain/order_email.html')
# Create your views here.
def home(request):
    return render(request, 'cardMain/home.html')

def basket(request):
    return render(request, 'cardMain/basket.html')

def about(request):
    return render(request, 'cardMain/about.html')

def contact(request):
    return render(request, 'cardMain/contact.html')

# handling contact form submissions
def contactform(request):
    """Handles contact form submissions."""

    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        contact_entry = Contacts(
            first_name=first_name,
            last_name=last_name,
            email=email,
            message=message
        )
        contact_entry.save()
    return render(request, 'cardMain/contact.html')

# for adding items to the basket
def add_to_basket(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        quantity = int(request.POST.get('quantity', 1))
        price = float(request.POST.get('price', 0.0))
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        # Try to get existing item, or create new
        try:
            basket_item = BasketItem.objects.get(session_id=session_id, product_name=product_name)
            basket_item.quantity += quantity  # Add to existing
            basket_item.save()
        except BasketItem.DoesNotExist:
            BasketItem.objects.create(
                session_id=session_id,
                product_name=product_name,
                quantity=quantity,
                price=price
            )
            messages.success(request, f"Added {quantity} of {product_name} to basket.")
        return render(request, 'cardMain/home.html', {'message': f'Added {quantity} of {product_name} to basket.'})

# for viewing the basket
def view_basket(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    basket_items = BasketItem.objects.filter(session_id=session_id)
    total = sum(item.price * item.quantity for item in basket_items)
    context = {'basket': basket_items, 'total': total}
    return render(request, 'cardMain/basket.html', context)

def clear_basket(request):
    session_id = request.session.session_key
    if session_id:
        BasketItem.objects.filter(session_id=session_id).delete()
    return redirect('basket')

# checkout view
def checkout(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    basket_items = BasketItem.objects.filter(session_id=session_id)
    total = sum(item.price * item.quantity for item in basket_items)
    context = {'basket': basket_items, 'total': total}
    return render(request, 'cardMain/checkout.html', context)

def make_order(request):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    basket_items = BasketItem.objects.filter(session_id=session_id)
    total = sum(item.price * item.quantity for item in basket_items)

    # Here you would typically create an order in your database
    if request.method == "POST":
        order_id = request.POST.get('order_id')
        customer_name = request.POST.get('first_name') + ' ' + request.POST.get('last_name')
        email = request.POST.get('email')
        product_name = ", ".join(f"{item.product_name} x{item.quantity}" for item in basket_items)
        quantity = sum(item.quantity for item in basket_items)
        total_price = total
        order_date = request.POST.get('order_date')
        delivery_address_line_1 = request.POST.get('address_line1')
        delivery_address_line_2 = request.POST.get('address_line2')
        delivery_city = request.POST.get('city')
        delivery_county = request.POST.get('county')
        delivery_post_code = request.POST.get('postal_code')

        order_entry = Orders(
            order_id=order_id,
            status='pending',
            customer_name=customer_name,
            email=email,
            product_name=product_name,
            quantity=quantity,
            total_price=total_price,
            order_date=order_date,
            delivery_address_line_1=delivery_address_line_1,
            delivery_address_line_2=delivery_address_line_2,
            delivery_city=delivery_city,
            delivery_county=delivery_county,
            delivery_post_code=delivery_post_code
        )
        order_entry.save()

        # Create order items
        for item in basket_items:
            OrderItem.objects.create(
                order=order_entry,
                product_name=item.product_name,
                quantity=item.quantity,
                price=item.price
            )
        context = {
            'order_entry': order_entry,
            'total': total,
            'paypal_email': settings.PAYPAL_RECEIVER_EMAIL,
            'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID,  # make sure this is passed
        }
        clear_basket(request)
        request.session['order_id'] = order_entry.order_id
        return render(request, 'cardMain/payment.html', context)

# PayPal REST API integration
import json
def get_access_token():
    """Retrieve OAuth access token from PayPal"""
    response = requests.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
        data={"grant_type": "client_credentials"}
    )
    response.raise_for_status()
    return response.json()["access_token"]

@csrf_exempt
def create_order(request):
    data = json.loads(request.body)
    total = data["total"]
    internal_order_id = data["order_id"]  # Pass from frontend

    access_token = get_access_token()
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": internal_order_id,  # 👈 our internal order
            "amount": {"currency_code": "GBP", "value": total}
        }],
        "application_context": {
            "brand_name": "Your Business Name",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW"
        }
    }

    response = requests.post(
        f"{PAYPAL_API_BASE}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=payload
    )
    return JsonResponse(response.json())

@csrf_exempt
def capture_order(request, order_id):
    access_token = get_access_token()
    response = requests.post(
        f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
    )
    capture_data = response.json()

    if capture_data.get("status") == "COMPLETED":
        internal_order_id = capture_data["purchase_units"][0]["reference_id"]
        order = Orders.objects.get(order_id=internal_order_id)
        order.status = "paid"
        order.save()

    return JsonResponse(capture_data)

import hmac
import hashlib

@csrf_exempt
def paypal_webhook(request):
    webhook_id = settings.PAYPAL_WEBHOOK_ID
    payload = request.body.decode('utf-8')
    headers = {
        'paypal-transmission-id': request.headers.get('Paypal-Transmission-Id'),
        'paypal-transmission-time': request.headers.get('Paypal-Transmission-Time'),
        'paypal-cert-url': request.headers.get('Paypal-Cert-Url'),
        'paypal-auth-algo': request.headers.get('Paypal-Auth-Algo'),
        'paypal-transmission-sig': request.headers.get('Paypal-Transmission-Sig'),
    }

    # Verify PayPal signature
    access_token = get_access_token()
    verify_resp = requests.post(
        f"{PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "auth_algo": headers['paypal-auth-algo'],
            "cert_url": headers['paypal-cert-url'],
            "transmission_id": headers['paypal-transmission-id'],
            "transmission_sig": headers['paypal-transmission-sig'],
            "transmission_time": headers['paypal-transmission-time'],
            "webhook_id": webhook_id,
            "webhook_event": json.loads(payload),
        }
    )

    verify_data = verify_resp.json()
    if verify_data.get("verification_status") != "SUCCESS":
        return JsonResponse({"status": "invalid signature"}, status=400)

    # Parse event
    event = json.loads(payload)
    event_type = event.get("event_type")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        # Get your internal order reference (sent as reference_id)
        try:
            reference_id = event["resource"]["supplementary_data"]["related_ids"]["order_id"]
        except KeyError:
            reference_id = event["resource"]["id"]

        try:
            order = Orders.objects.get(order_id=reference_id)
        except Orders.DoesNotExist:
            return JsonResponse({"status": "order not found"}, status=404)

        # Update order status
        order.status = "paid"
        order.save()

        # ✅ Send confirmation email
        subject = f"Order Confirmation - Order #{order.order_id}"
        html_message = render_to_string('cardMain/order_email.html', {
            'order_entry': order,
            'items': order.orderitem_set.all(),
            'total': order.total_price,
        })

        send_mail(
            subject,
            '',  # plain-text fallback
            settings.DEFAULT_FROM_EMAIL,  # sender
            [order.email],                # recipient
            html_message=html_message
        )

    return JsonResponse({"status": "success"})

# last part 
def order_confirmation(request):
    order_id = request.session.get('order_id')
    order_entry = Orders.objects.filter(order_id=order_id).first()
    total = order_entry.total_price if order_entry else 0
    context = {'order_entry': order_entry, 'total': total}
        
    return render(request, 'cardMain/order_confirmation.html', context)