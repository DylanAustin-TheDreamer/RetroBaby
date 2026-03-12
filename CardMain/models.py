from django.db import models
from django.contrib.sessions.models import Session

# Create your models here.
class Orders(models.Model):
    order_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, default='pending')
    customer_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    product_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    delivery_address_line_2 = models.CharField(max_length=255, blank=True, null=True)  # Optional
    delivery_city = models.CharField(max_length=100, blank=True, null=True)
    delivery_county = models.CharField(max_length=100, blank=True, null=True)
    delivery_post_code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Order {self.order_id} - {self.product_name} x{self.quantity} for {self.customer_name}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Orders, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity} - ${self.price}"
    
# Contact model for contact form submissions    
class Contacts(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact {self.first_name} {self.last_name} from {self.email}"

class BasketItem(models.Model):
    session_id = models.CharField(max_length=255)  # Session key length
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session_id', 'product_name')  # One entry per product per session
    def __str__(self):
        return f"{self.product_name} x{self.quantity} - ${self.price}"
    