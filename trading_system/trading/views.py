from django.shortcuts import render, redirect
from .models import User, Order, Trade
from django.db.models import Q
from django.db import transaction
from .utils import match_order  # Assuming match_order is in utils.py
from django.http import JsonResponse

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        user, created = User.objects.get_or_create(username=username)
        return redirect('home', user_id=user.id)
    return render(request, 'trading/login.html')
from django.shortcuts import render
from .models import Order

def home(request, user_id):
    user = User.objects.get(id=user_id)

    if request.method == "POST":
        order_type = request.POST.get('order_type')
        order_mode = request.POST.get('order_mode')
        quantity = int(request.POST.get('quantity'))
        
        price = None
        
        if order_mode == "LIMIT":
            price = float(request.POST.get('price', 0))  # Default to 0 if no price is provided
        
        elif order_mode == "MARKET":
            if order_type == "BUY":
                price = get_best_ask_price()  # Fetch best ask price for a buy order
            elif order_type == "SELL":
                price = get_best_bid_price()  # Fetch best bid price for a sell order
            
            if price is None:
                return render(request, 'trading/home.html', {'error': 'Unable to fetch market price for the order type.'})
        
        # Create and save the new order
        new_order = Order(
            order_type=order_type,
            order_mode=order_mode,
            quantity=quantity,
            price=price,
            is_matched=False,
            user=user  # Ensure the order is associated with the user
        )
        new_order.save()

        match_order(new_order)

    # Fetch orders associated with the user
    orders = Order.objects.filter(user=user)  # Adjust query to filter by user_id

    return render(request, 'trading/home.html', {'user':user,'orders': orders})


def get_best_ask_price(request):
    # Fetch the best ask price (lowest available price for a buy order)
    best_ask = Order.objects.filter(order_type="SELL", is_matched=False).order_by('price').first()
    if best_ask:
        return JsonResponse({'best_ask_price': best_ask.price})
    return JsonResponse({'best_ask_price': None})

def get_best_bid_price(request):
    # Fetch the best bid price (highest available price for a sell order)
    best_bid = Order.objects.filter(order_type="BUY", is_matched=False).order_by('-price').first()
    if best_bid:
        return JsonResponse({'best_bid_price': best_bid.price})
    return JsonResponse({'best_bid_price': None})


from django.shortcuts import render
from .models import Order
from django.shortcuts import render
from .models import Order, Trade

def orderbook(request):
    # Retrieve unmatched buy orders (sorted by price in descending order)
    buy_orders = Order.objects.filter(is_matched=False, order_type='BUY').order_by('-price')
    # Retrieve unmatched sell orders (sorted by price in ascending order)
    sell_orders = Order.objects.filter(is_matched=False, order_type='SELL').order_by('price')
    
    # Retrieve all trades (you may filter or sort as needed)
    trades = Trade.objects.all().order_by('-timestamp')  # Sorting trades by timestamp
    
    # Display both buy and sell orders in the orderbook, along with trades
    return render(request, 'trading/orderbook.html', {
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
        'best_bid': buy_orders.first() if buy_orders else None,
        'best_ask': sell_orders.first() if sell_orders else None,
        'trades': trades  # Pass trades to the template
    })

def clear_database(request):
    Order.objects.all().delete()
    Trade.objects.all().delete()
    return redirect('login')
