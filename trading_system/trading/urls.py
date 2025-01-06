from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'trading'

urlpatterns = [
    # Authentication Views
    path('', LoginView.as_view(), name='login'),  
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  

    # Main Views
    path('home/', HomeView.as_view(), name='home'),  
    path('orderbook/', OrderBookView.as_view(), name='orderbook'),  
    path('clear/', ClearDatabaseView.as_view(), name='clear_database'), 

    # API Endpoints
    path('api/get_best_ask/', BuyOrdersAPIView.as_view(), name='get_best_ask'),  
    path('api/get_best_bid/', SellOrdersAPIView.as_view(), name='get_best_bid'),  
    path('api/get_buy_orders/', BuyOrdersAPIView.as_view(), name='get_buy_orders'),  
    path('api/get_sell_orders/', SellOrdersAPIView.as_view(), name='get_sell_orders'),  
    path('api/get_recent_trades/', RecentTradesAPIView.as_view(), name='get_recent_trades'),  
]
