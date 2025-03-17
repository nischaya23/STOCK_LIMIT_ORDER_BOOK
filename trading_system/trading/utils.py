from django.db import transaction
from django.utils import timezone
from .models import Order, Trade

def match_order(new_order):
    """
    Match an order with compatible orders in the orderbook.
    Now handles all order types including stop market and stop limit orders.
    """
    # Skip processing if it's a stop order that hasn't been triggered yet
    if new_order.order_mode in ['STOP_MARKET', 'STOP_LIMIT'] and not new_order.is_triggered:
        # Stop orders wait to be triggered by market conditions
        return

    # Begin a transaction to ensure atomicity
    with transaction.atomic():
        # For a BUY limit order, we are looking for SELL orders at the same price or lower
        if new_order.order_type == 'BUY' and new_order.order_mode in ['LIMIT', 'STOP_LIMIT']:
            opposite_orders = Order.objects.filter(
                order_type='SELL', 
                order_mode__in=['LIMIT', 'STOP_LIMIT'],
                price__lte=new_order.price, 
                is_matched=False
            ).order_by('price', 'timestamp')
        
        # For a SELL limit order, we are looking for BUY orders at the same price or higher
        elif new_order.order_type == 'SELL' and new_order.order_mode in ['LIMIT', 'STOP_LIMIT']:
            opposite_orders = Order.objects.filter(
                order_type='BUY', 
                order_mode__in=['LIMIT', 'STOP_LIMIT'],
                price__gte=new_order.price, 
                is_matched=False
            ).order_by('-price', 'timestamp')

        # For market orders (including triggered stop market orders), match at best available price
        # SELL market order
        elif new_order.order_mode in ['MARKET', 'STOP_MARKET']:
            if new_order.order_type == 'BUY':
                opposite_orders = Order.objects.filter(
                    order_type='SELL', 
                    is_matched=False
                ).order_by('price', 'timestamp')
            else:  
                opposite_orders = Order.objects.filter(
                    order_type='BUY', 
                    is_matched=False
                ).order_by('-price', 'timestamp')

        # Immediate or Cancellation (IOC) orders
        if new_order.is_ioc:
            # Track executed quantity for IOC orders
            executed_quantity=0
            
            for opposite_order in opposite_orders:
                if new_order.quantity<=0:
                    break
                
                match_quantity=min(new_order.quantity,opposite_order.quantity)
                
                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price=opposite_order.price,
                    timestamp=timezone.now()
                )
                
                # Update quantities
                executed_quantity += match_quantity
                new_order.quantity -= match_quantity
                opposite_order.quantity -= match_quantity
                
                # Update disclosed quantity if needed
                if(opposite_order.disclosed>opposite_order.quantity):# < to > Akshat
                    opposite_order.disclosed=opposite_order.quantity
                if(new_order.disclosed>new_order.quantity):# < to > Akshat
                    new_order.disclosed=new_order.quantity
                
                # Update opposite order status
                if opposite_order.quantity == 0:
                    opposite_order.is_matched = True
                opposite_order.save()
            
            # Handle IOC order after matching
            if executed_quantity>0:
                # Partially executed:save with executed quantity and mark as matched
                new_order.quantity=0  # Discard remaining quantity
                new_order.is_matched=True
                new_order.disclosed=0 
                print("saved1")
                new_order.save()
                return  # To prevent further processing
            else:
                # Completely unexecuted:delete the order
                print("delete1")
                new_order.delete()
                return

        # Try to match with the opposite orders
        if new_order.order_mode in ["LIMIT", "STOP_LIMIT"]:
            remaining_quantity = new_order.quantity
            for opposite_order in opposite_orders:
                if remaining_quantity <= 0:
                    break
                
                match_quantity = min(remaining_quantity, opposite_order.quantity)
                match_price = opposite_order.price

                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price=match_price,
                    timestamp=timezone.now()
                )

                # Update the quantities of the matched orders
                remaining_quantity -= match_quantity
                opposite_order.quantity -= match_quantity
                new_order.quantity -= match_quantity
                if(opposite_order.disclosed>opposite_order.quantity):# < to > Akshat
                    opposite_order.disclosed=opposite_order.quantity
                if(new_order.disclosed>new_order.quantity):# < to > Akshat
                    new_order.disclosed=new_order.quantity
                opposite_order.save()
                new_order.save()

                # If the opposite order is fully matched, mark it as matched
                if opposite_order.quantity == 0:
                    opposite_order.is_matched = True
                    opposite_order.save()

                # If the new order is fully matched, mark it as matched
                if new_order.quantity == 0:
                    new_order.is_matched = True
                    new_order.save()

            # If the new order is partially matched, update its quantity and status
            if new_order.quantity > 0:
                new_order.save()
            else:
                new_order.is_matched = True
                new_order.save()

            # Ensure that any remaining unmatched orders are still available for future matches
             # MARKET order or STOP_MARKET order processing
            new_order.timestamp = timezone.now()
            new_order.save()
        else: 
            remaining_quantity = new_order.quantity
            complete_order = False
            try:
                for opposite_order in opposite_orders:
                    if remaining_quantity <= 0:
                        complete_order = True
                        break
                    
                    match_quantity = min(opposite_order.quantity, remaining_quantity)
                    if match_quantity == opposite_order.quantity:
                        Trade.objects.create(
                            buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                            seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                            quantity=match_quantity,
                            price=opposite_order.price,
                            timestamp=timezone.now()
                        )
                        remaining_quantity -= match_quantity
                        opposite_order.quantity -= match_quantity
                        new_order.quantity -= match_quantity
                        if(opposite_order.disclosed>opposite_order.quantity):# < to > Akshat
                            opposite_order.disclosed=opposite_order.quantity
                        if(new_order.disclosed>new_order.quantity):# < to > Akshat
                            new_order.disclosed=new_order.quantity
                        opposite_order.is_matched = True
                        opposite_order.save()
                        new_order.save()
                    else:
                        Trade.objects.create(
                            buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                            seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                            quantity=match_quantity,
                            price=opposite_order.price,
                            timestamp=timezone.now()
                        )
                        remaining_quantity -= match_quantity
                        opposite_order.quantity -= match_quantity
                        new_order.quantity -= match_quantity
                        opposite_order.save()
                        new_order.save()
            except Exception as e:
                print(f'Error occurred during matching: {str(e)}')
            
            if complete_order == False and remaining_quantity > 0:
                # The leftover quantity is converted to 0 for market orders
                remaining_quantity = 0
                new_order.quantity = 0
                new_order.is_matched = True
                new_order.save()
                print("Incomplete order Placed")

def check_and_trigger_stop_loss_orders():
    """
    Check if any stop loss orders should be triggered based on current market conditions
    and convert them to appropriate order types if conditions are met.
    """
    # Get current market prices
    best_ask = get_best_ask_price()
    best_bid = get_best_bid_price()
    
    if best_ask is not None and best_bid is not None:
        # Find all BUY stop orders that should trigger (when market price falls to or below stop price)
         # Trigger when market price is at or below stop price
        buy_stop_orders = Order.objects.filter(
            order_mode__in=["STOP_MARKET", "STOP_LIMIT"],
            order_type="BUY",
            is_matched=False,
            is_triggered=False,
            stop_price__gte=best_ask 
        )
        
        # Find all SELL stop orders that should trigger (when market price rises to or above stop price)
         # Trigger when market price is at or above stop price
        sell_stop_orders = Order.objects.filter(
            order_mode__in=["STOP_MARKET", "STOP_LIMIT"],
            order_type="SELL",
            is_matched=False,
            is_triggered=False,
            stop_price__lte=best_bid 
        )
        
        # Process triggered stop orders
        for order in list(buy_stop_orders) + list(sell_stop_orders):
            order.is_triggered = True
            
            if order.order_mode == "STOP_MARKET":
                # Convert stop market to market order
                order.order_mode = "MARKET"
                order.price = best_ask if order.order_type == "BUY" else best_bid
            
            elif order.order_mode == "STOP_LIMIT":
                # Convert stop limit to limit order with the specified limit price
                order.order_mode = "LIMIT"
                order.price = order.limit_price
            
            order.save()
            
            # Execute the triggered order
            match_order(order)

def get_best_ask_price():
    """Helper function to get the best ask price"""
    best_ask = Order.objects.filter(
        order_type="SELL", 
        order_mode__in=["LIMIT", "MARKET", "STOP_LIMIT"],
        is_matched=False
    ).order_by('price').values('price').first()
    
    return best_ask['price'] if best_ask else None

def get_best_bid_price():
    """Helper function to get the best bid price"""
    best_bid = Order.objects.filter(
        order_type="BUY", 
        order_mode__in=["LIMIT", "MARKET", "STOP_LIMIT"],
        is_matched=False
    ).order_by('-price').values('price').first()
    
    return best_bid['price'] if best_bid else None