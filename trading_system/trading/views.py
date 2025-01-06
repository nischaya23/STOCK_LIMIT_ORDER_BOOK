from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db import transaction

from .models import User, Order, Trade
from .utils import match_order


# Login View
class LoginView(View):
    def get(self, request):
        return render(request, 'trading/login.html')

    def post(self, request):
        username = request.POST.get('username')
        user, created = User.objects.get_or_create(username=username)
        return redirect('trading:home')


# Helper Methods
def fetch_best_ask():
    """Fetch the best ask price (lowest available price for a buy order)."""
    return Order.objects.filter(order_type="SELL", is_matched=False).order_by('price').values('price', 'quantity').first()


def fetch_best_bid():
    """Fetch the best bid price (highest available price for a sell order)."""
    return Order.objects.filter(order_type="BUY", is_matched=False).order_by('-price').values('price', 'quantity').first()


# Home View
class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user)  # Fetch user-specific orders
        return render(request, 'trading/home.html', {'user': user, 'orders': orders})

    def post(self, request):
        user = request.user

        order_type = request.POST.get('order_type')
        order_mode = request.POST.get('order_mode')
        quantity = int(request.POST.get('quantity'))

        price = None

        if order_mode == "LIMIT":
            price = float(request.POST.get('price', 0))  # Default to 0 if no price is provided

        elif order_mode == "MARKET":
            if order_type == "BUY":
                best_ask_data = fetch_best_ask()
                if best_ask_data:
                    price = best_ask_data['price']

            elif order_type == "SELL":
                best_bid_data = fetch_best_bid()
                if best_bid_data:
                    price = best_bid_data['price']

            if price is None:
                return render(request, 'trading/home.html', {'error': 'Unable to fetch market price for the order type.'})

        # Create and save the new order
        new_order = Order(
            order_type=order_type,
            order_mode=order_mode,
            quantity=quantity,
            price=price,
            is_matched=False,
            user=user
        )
        new_order.save()

        # Match the new order
        match_order(new_order)

        # Fetch updated user-specific orders
        orders = Order.objects.filter(user=user)
        return render(request, 'trading/home.html', {'user': user, 'orders': orders})


# OrderBook View
class OrderBookView(View):
    def get(self, request):
        buy_orders = Order.objects.filter(is_matched=False, order_type='BUY').order_by('-price')
        sell_orders = Order.objects.filter(is_matched=False, order_type='SELL').order_by('price')
        trades = Trade.objects.all().order_by('-timestamp')  # Recent trades

        return render(request, 'trading/orderbook.html', {
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'best_bid': buy_orders.first() if buy_orders else None,
            'best_ask': sell_orders.first() if sell_orders else None,
            'trades': trades
        })


# Clear Database View
class ClearDatabaseView(View):
    def get(self, request):
        Order.objects.all().delete()
        Trade.objects.all().delete()
        return redirect('trading:login')


# API Views
class BestAskAPIView(View):
    def get(self, request):
        best_ask = fetch_best_ask()
        return JsonResponse({'best_ask': best_ask})


class BestBidAPIView(View):
    def get(self, request):
        best_bid = fetch_best_bid()
        return JsonResponse({'best_bid': best_bid})


class BuyOrdersAPIView(View):
    def get(self, request):
        buy_orders = Order.objects.filter(order_type='BUY', is_matched=False).values('price', 'quantity', 'is_matched')
        return JsonResponse({'buy_orders': list(buy_orders)})


class SellOrdersAPIView(View):
    def get(self, request):
        sell_orders = Order.objects.filter(order_type='SELL', is_matched=False).values('price', 'quantity', 'is_matched')
        return JsonResponse({'sell_orders': list(sell_orders)})


class RecentTradesAPIView(View):
    def get(self, request):
        recent_trades = Trade.objects.all().order_by('-timestamp')[:10].values(
            'buyer', 'seller', 'price', 'quantity', 'timestamp'
        )
        return JsonResponse({'trades': list(recent_trades)})
