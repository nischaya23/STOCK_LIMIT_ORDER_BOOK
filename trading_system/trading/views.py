from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
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
        return redirect('home', user_id=user.id)


# Home View
@method_decorator(login_required, name='dispatch')
class HomeView(View):
    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user)  # Orders associated with the logged-in user
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
                price = self.get_best_ask()
            elif order_type == "SELL":
                price = self.get_best_bid()

            if price is None:
                return render(request, 'trading/home.html', {
                    'error': 'Unable to fetch market price for the order type.'
                })

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
        match_order(new_order)

        orders = Order.objects.filter(user=user)
        return render(request, 'trading/home.html', {'user': user, 'orders': orders})

    def get_best_ask(self):
        best_ask = Order.objects.filter(order_type="SELL", is_matched=False).order_by('price').first()
        return best_ask.price if best_ask else None

    def get_best_bid(self):
        best_bid = Order.objects.filter(order_type="BUY", is_matched=False).order_by('-price').first()
        return best_bid.price if best_bid else None


# Order Book View
class OrderBookView(TemplateView):
    template_name = 'trading/orderbook.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['buy_orders'] = Order.objects.filter(is_matched=False, order_type='BUY').order_by('-price')
        context['sell_orders'] = Order.objects.filter(is_matched=False, order_type='SELL').order_by('price')
        context['trades'] = Trade.objects.all().order_by('-timestamp')
        context['best_bid'] = context['buy_orders'].first() if context['buy_orders'] else None
        context['best_ask'] = context['sell_orders'].first() if context['sell_orders'] else None
        return context


# Clear Database View
class ClearDatabaseView(View):
    def get(self, request):
        Order.objects.all().delete()
        Trade.objects.all().delete()
        return redirect('auth:login')


# API Views
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
