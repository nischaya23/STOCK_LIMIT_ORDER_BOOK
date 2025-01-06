from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'trading'  

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='trading/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('orderbook/', views.OrderBookView.as_view(), name='orderbook'),
    path('clear/', views.ClearDatabaseView.as_view(), name='clear_database'),
    path('orderbook/get_best_ask/', views.BestAskAPIView.as_view(), name='get_best_ask'),
    path('orderbook/get_best_bid/', views.BestBidAPIView.as_view(), name='get_best_bid'),
    path('orderbook/get_buy_orders/', views.BuyOrdersAPIView.as_view(), name='get_buy_orders'),
    path('orderbook/get_sell_orders/', views.SellOrdersAPIView.as_view(), name='get_sell_orders'),
    path('orderbook/get_recent_trades/', views.RecentTradesAPIView.as_view(), name='get_recent_trades'),
]
