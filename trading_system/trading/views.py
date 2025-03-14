from django.shortcuts import render, redirect
from .models import User, Order, Trade
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.decorators import login_required
import json

from .utils import match_order, check_and_trigger_stop_loss_orders
from django.http import JsonResponse

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        user, created = User.objects.get_or_create(username=username)
        return redirect('home', user_id=user.id)
    return render(request, 'trading/login.html')

def fetch_best_ask():
    # Fetch the best ask price (lowest available price for a buy order)
    return Order.objects.filter(
        order_type="SELL", 
        is_matched=False,
        order_mode__in=["LIMIT", "MARKET"]
    ).order_by('price').values('price', 'quantity').first()

def fetch_best_bid():
    # Fetch the best bid price (highest available price for a sell order)
    return Order.objects.filter(
        order_type="BUY", 
        is_matched=False,
        order_mode__in=["LIMIT", "MARKET"]
    ).order_by('-price').values('price', 'quantity').first()

def get_best_ask(request):
    if request.method == 'GET':
        # Fetch the best ask price
        best_ask = fetch_best_ask()
        return JsonResponse({'best_ask': best_ask})
    return JsonResponse({'best_ask': None})

def get_best_bid(request):
    if request.method == 'GET':
        # Fetch the best bid price
        best_bid = fetch_best_bid()
        return JsonResponse({'best_bid': best_bid})
    return JsonResponse({'best_bid': None})

@login_required  
def home(request):
    user = request.user  
    user, created = User.objects.get_or_create(username=user)

    error_message = None

    # Check for any stop loss orders that should be triggered
    check_and_trigger_stop_loss_orders()

    if request.method == "POST":
        order_type = request.POST.get('order_type')
        order_mode = request.POST.get('order_mode')
        quantity = int(request.POST.get('quantity'))
        price = None
        stop_price = None
        limit_price = None

        try:
            # Handle different order modes
            if order_mode == "LIMIT":
                price = float(request.POST.get('price', 0))
            
            elif order_mode == "STOP_MARKET":
                # For stop market orders, get the stop price
                stop_price = float(request.POST.get('stop_price', 0))
                # Price will be set when the order is triggered
                price = None
            
            elif order_mode == "STOP_LIMIT":
                # For stop limit orders, get both stop price and limit price
                stop_price = float(request.POST.get('stop_price', 0))
                limit_price = float(request.POST.get('limit_price', 0))
                # Price will be set to limit_price when the order is triggered
                price = None
            
            elif order_mode == "MARKET":
                if order_type == "BUY":
                    # Fetch the best ask for market buy orders
                    best_ask_response = fetch_best_ask()
                    if best_ask_response:
                        price = best_ask_response['price']
                    else:
                        error_message = 'No sell orders available for market buy.'
                        return render(request, 'trading/home.html', {
                            'user': user, 
                            'orders': Order.objects.filter(user=user),
                            'error': error_message
                        })

                elif order_type == "SELL":
                    # Fetch the best bid for market sell orders
                    best_bid_response = fetch_best_bid()
                    if best_bid_response:
                        price = best_bid_response['price']
                    else:
                        error_message = 'No buy orders available for market sell.'
                        return render(request, 'trading/home.html', {
                            'user': user, 
                            'orders': Order.objects.filter(user=user),
                            'error': error_message
                        })

            # Create and save the new order
            new_order = Order(
                order_type=order_type,
                order_mode=order_mode,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                limit_price=limit_price,
                is_matched=False,
                is_triggered=False,
                user=user
            )
            new_order.save()
            
            # Only attempt to match non-stop orders immediately
            if order_mode not in ["STOP_MARKET", "STOP_LIMIT"]:
                match_order(new_order)
            else:
                # Check if the stop order should be triggered immediately
                check_and_trigger_stop_loss_orders()
                
        except Exception as e:
            error_message = f'Error processing order: {str(e)}'
            
    # Fetch orders associated with the user
    orders = Order.objects.filter(user=user)

    return render(request, 'trading/home.html', {
        'user': user, 
        'orders': orders,
        'error': error_message
    })

def orderbook(request):
    # Check for any stop loss orders that should be triggered
    check_and_trigger_stop_loss_orders()
    
    # Retrieve unmatched buy orders (sorted by price in descending order)
    buy_orders = Order.objects.filter(
        is_matched=False, 
        order_type='BUY', 
        order_mode__in=['LIMIT', 'MARKET']
    ).order_by('-price')
    
    # Retrieve unmatched sell orders (sorted by price in ascending order)
    sell_orders = Order.objects.filter(
        is_matched=False, 
        order_type='SELL', 
        order_mode__in=['LIMIT', 'MARKET']
    ).order_by('price')
    
    # Get stop market orders (for display purposes)
    stop_market_orders = Order.objects.filter(
        is_matched=False,
        is_triggered=False,
        order_mode='STOP_MARKET'
    ).order_by('order_type', 'stop_price')
    
    # Get stop limit orders (for display purposes)
    stop_limit_orders = Order.objects.filter(
        is_matched=False,
        is_triggered=False,
        order_mode='STOP_LIMIT'
    ).order_by('order_type', 'stop_price')
    
    # Retrieve all trades (you may filter or sort as needed)
    trades = Trade.objects.all().order_by('-timestamp')
    
    # Display all orders in the orderbook, along with trades
    return render(request, 'trading/orderbook.html', {
        'buy_orders': buy_orders,
        'sell_orders': sell_orders,
        'stop_market_orders': stop_market_orders,
        'stop_limit_orders': stop_limit_orders,
        'best_bid': buy_orders.first() if buy_orders else None,
        'best_ask': sell_orders.first() if sell_orders else None,
        'trades': trades
    })

def clear_database(request):
    Order.objects.all().delete()
    Trade.objects.all().delete()
    return redirect('login')

def get_buy_orders(request):
    if request.method == 'GET':
        buy_orders = Order.objects.filter(
            order_type='BUY', 
            is_matched=False,
            order_mode__in=['LIMIT', 'MARKET']
        ).values('price', 'quantity', 'is_matched')
        return JsonResponse({'buy_orders': list(buy_orders)})

def get_sell_orders(request):
    if request.method == 'GET':
        sell_orders = Order.objects.filter(
            order_type='SELL', 
            is_matched=False,
            order_mode__in=['LIMIT', 'MARKET']
        ).values('price', 'quantity', 'is_matched')
        return JsonResponse({'sell_orders': list(sell_orders)})

def get_stop_market_orders(request):
    if request.method == 'GET':
        stop_market_orders = Order.objects.filter(
            order_mode='STOP_MARKET', 
            is_matched=False,
            is_triggered=False
        ).values('order_type', 'stop_price', 'quantity')
        return JsonResponse({'stop_market_orders': list(stop_market_orders)})

def get_stop_limit_orders(request):
    if request.method == 'GET':
        stop_limit_orders = Order.objects.filter(
            order_mode='STOP_LIMIT', 
            is_matched=False,
            is_triggered=False
        ).values('order_type', 'stop_price', 'limit_price', 'quantity')
        return JsonResponse({'stop_limit_orders': list(stop_limit_orders)})

def get_recent_trades(request):
    if request.method == 'GET':
        recent_trades = Trade.objects.all().order_by('-timestamp')[:10].values(
            'buyer', 'seller', 'price', 'quantity', 'timestamp'
        )
        return JsonResponse({'trades': list(recent_trades)})