from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('home/<int:user_id>/', views.home, name='home'),
    path('orderbook/', views.orderbook, name='orderbook'),
    path('clear/', views.clear_database, name='clear_database'),
    path('get_best_ask_price/', views.get_best_ask_price, name='get_best_ask_price'),
    path('get_best_bid_price/', views.get_best_bid_price, name='get_best_bid_price'),
]
