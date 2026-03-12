from django.urls import path, include
from . import views  # Import your views
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', views.home, name='home'),  # Root URL for the app (e.g., /)
    # testing email page
    path('test_email/', views.test_email_view, name='test_email'),
    # Add more paths here, e.g.:
    # path('about/', views.about, name='about'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('order_confirmation/', views.order_confirmation, name='order_confirmation'),
    path('order_cancelled/', views.order_confirmation, name='order_confirmation'),
    path('payment/', views.make_order, name='payment'),
    path('contactform/', views.contactform, name='contactform'),
    path('add_to_basket/', views.add_to_basket, name='add_to_basket'),
    path('basket/', views.view_basket, name='basket'),
    path('clear_basket/', views.clear_basket, name='clear_basket'),
    path('checkout/', views.checkout, name='checkout'),
    path('make_order/', views.make_order, name='make_order'),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path("api/paypal/create-order/", views.create_order, name="paypal-create-order"),
    path("api/paypal/capture-order/<str:order_id>/", views.capture_order, name="paypal-capture-order"),
]