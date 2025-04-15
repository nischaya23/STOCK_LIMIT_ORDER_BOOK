from django.db import transaction
from django.utils import timezone
from .models import Order, Trade
from .models import Stoploss_Order as StopLossOrder
from django.db.models import F
from datetime import timedelta


def match_order(new_order):
    print("match")
    # changes
    closing_price= None
    # Begin a transaction to ensure atomicity
    with transaction.atomic():
        # For a BUY limit order, we are looking for SELL orders at the same price or lower
        if new_order.order_type == 'BUY' and new_order.order_mode == 'LIMIT':
            opposite_orders = Order.objects.filter(
                order_type='SELL', 
                order_mode='LIMIT', 
                price__lte=new_order.price, 
                is_matched=False
            ).order_by('price', 'timestamp')
        
        # For a SELL limit order, we are looking for BUY orders at the same price or higher
        elif new_order.order_type == 'SELL' and new_order.order_mode == 'LIMIT':
            opposite_orders = Order.objects.filter(
                order_type='BUY', 
                order_mode='LIMIT', 
                price__gte=new_order.price, 
                is_matched=False
            ).order_by('-price', 'timestamp')

        # For a BUY market order, we are looking for SELL orders with the lowest price
        elif new_order.order_type == 'BUY' and new_order.order_mode == 'MARKET':
            opposite_orders = Order.objects.filter(
                order_type='SELL', 
                is_matched=False
            ).order_by('price', 'timestamp')

        # For a SELL market order, we are looking for BUY orders with the highest price
        elif new_order.order_type == 'SELL' and new_order.order_mode == 'MARKET':
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
                
                closing_price= opposite_order.price
                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price=closing_price,
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
                return # To prevent further processing
            else:
                # Completely unexecuted:delete the order
                print("delete1")
                new_order.delete()
                return

        # Try to match with the opposite orders
        if(new_order.order_mode=="LIMIT"):
            remaining_quantity = new_order.quantity
            for opposite_order in opposite_orders:
                if remaining_quantity <= 0:
                    break
                
                match_quantity = min(remaining_quantity, opposite_order.quantity)
                closing_price = opposite_order.price if new_order.order_mode == 'LIMIT' else opposite_order.price

        
                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price= closing_price,
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
            
            new_order.timestamp = timezone.now()
            process_stoploss_orders(closing_price)
            new_order.save()
            
        else:
            
            remaining_quantity=new_order.quantity
            complete_order=False
            # while(remaining_quantity>0):
            try:
                for opposite_order in opposite_orders:
                    if(remaining_quantity<=0):
                        complete_order=True
                        break
                    match_quantity=min(opposite_order.quantity,remaining_quantity)
                    closing_price=opposite_order.price
                    if(match_quantity==opposite_order.quantity):
                        Trade.objects.create(
                            buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                            seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                            quantity=match_quantity,
                            price=opposite_order.price,
                            timestamp=timezone.now()
                        )
                        print("123")
                        remaining_quantity-=match_quantity
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
                            price=closing_price,
                            timestamp=timezone.now()
                        )
                        remaining_quantity-=match_quantity
                        opposite_order.quantity -= match_quantity
                        new_order.quantity -= match_quantity
                        if(opposite_order.disclosed>opposite_order.quantity):# < to > Akshat
                            opposite_order.disclosed=opposite_order.quantity
                        if(new_order.disclosed>new_order.quantity):# < to > Akshat
                            new_order.disclosed=new_order.quantity
                        if(match_quantity == opposite_order.quantity):
                            opposite_order.is_matched = True
                        opposite_order.save()
                        new_order.save()
            except Exception as e:
                print('Some Error Occured')
            
            if(complete_order==False):
                #the leftover quantity is converted to 0
                remaining_quantity=0
                new_order.quantity=0
                new_order.is_matched=True
                new_order.save()
                print("Incomplete order Placed")
            
            process_stoploss_orders(closing_price)
               


def process_stoploss_orders(closing_price):
    """
    Update and sort stoploss orders after a trade execution
    """
    if closing_price is None:
        return
    with transaction.atomic():
        # Get all active stoploss orders
        active_stoploss_orders = StopLossOrder.objects.filter(is_matched=False)
        
        # Check each stoploss order against the closing price
        for stoploss_order in active_stoploss_orders:
            should_trigger = False
            
            if stoploss_order.order_type == 'BUY' and stoploss_order.target_price <= closing_price:
                should_trigger = True
            elif stoploss_order.order_type == 'SELL' and stoploss_order.target_price >= closing_price:
                should_trigger = True
            
            if should_trigger:
                # Create a new regular order
                new_order = Order(
                    order_type=stoploss_order.order_type,
                    order_mode=stoploss_order.order_mode,
                    quantity=stoploss_order.quantity,
                    disclosed=stoploss_order.disclosed,
                    price=stoploss_order.price,
                    is_matched=False,
                    is_ioc=False,
                    user=stoploss_order.user,
                    original_quantity=stoploss_order.quantity
                )
                new_order.save()
                
                
                # Mark stoploss order as matched
                stoploss_order.is_matched = True
                stoploss_order.save()
                
                # Attempt to match the new order
                match_order(new_order)
def get_sorted_stoploss_orders():   
        # Sort BUY stoploss orders by target price (ascending)
    buy_stoploss = StopLossOrder.objects.filter(
        order_type='BUY',
        is_matched=False
    ).order_by('target_price', 'timestamp')
        
        # Sort SELL stoploss orders by target price (descending)
    sell_stoploss = StopLossOrder.objects.filter(
        order_type='SELL',
        is_matched=False
    ).order_by('-target_price', 'timestamp')
                
            
def get_triggered_stoploss_orders(closing_price):
    """
    Get stoploss orders that were triggered by the current closing price
    These will be displayed in the recent orders table (regular Order table)
    """
    if closing_price is None:
        return Order.objects.none()
    
    # Get orders that were converted from stoploss orders
    # We can identify them by checking if original_quantity matches quantity (assuming this indicates fresh orders)
    triggered_orders = Order.objects.filter(
        timestamp__gte=timezone.now() - timedelta(minutes=5),  # Orders from last 5 minutes
        original_quantity=F('quantity'),  # Assuming this indicates newly created orders
        is_matched=False
    ).order_by('-timestamp')
    
    return triggered_orders



