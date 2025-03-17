from django.db import models
from django.utils.timezone import now


class User(models.Model):
    username = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.username

from datetime import datetime

class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]

    ORDER_MODE_CHOICES = [
        ('LIMIT', 'Limit'),
        ('MARKET', 'Market'),
        ('STOP_MARKET', 'Stop Market'),
        ('STOP_LIMIT', 'Stop Limit')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    order_mode = models.CharField(max_length=15, choices=ORDER_MODE_CHOICES)
    quantity = models.IntegerField()
    disclosed = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    limit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_matched = models.BooleanField(default=False)
    is_triggered = models.BooleanField(default=False)  

class Trade(models.Model):
    buyer = models.ForeignKey(User, related_name='buy_trades', on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name='sell_trades', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)