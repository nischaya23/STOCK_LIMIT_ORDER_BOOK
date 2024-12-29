from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='trading/login.html'), name='login'),
    path('/logout', auth_views.LogoutView.as_view(), name='logout'),
    path('home/', views.home, name='home'),
    path('orderbook/', views.orderbook, name='orderbook'),
    path('clear/', views.clear_database, name='clear_database'),
    path('get_best_ask_price/', views.get_best_ask_price, name='get_best_ask_price'),
    path('get_best_bid_price/', views.get_best_bid_price, name='get_best_bid_price'),
]
