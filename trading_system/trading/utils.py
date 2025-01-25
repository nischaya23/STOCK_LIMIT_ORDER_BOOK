from django.db import transaction
from django.utils import timezone
from .models import Order, Trade

def match_order(new_order):
    # Begin a transaction to ensure atomicity
    with transaction.atomic():
        # Track if any execution occurred for IOC orders
        executed_quantity=0
        
        # For a BUY limit order, we are looking for SELL orders at the same price or lower
        if new_order.order_type=='BUY' and new_order.order_mode=='LIMIT':
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
        
        # If this is an IOC order
        if new_order.is_ioc:
            for opposite_order in opposite_orders:
                if new_order.quantity <= 0:
                    break
                
                match_quantity = min(new_order.quantity, opposite_order.quantity)
                
                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price=opposite_order.price,
                    timestamp=timezone.now()
                )
                
                # Update quantities and track execution
                executed_quantity += match_quantity
                new_order.quantity -= match_quantity
                opposite_order.quantity -= match_quantity
                
                # If opposite order is fully matched, mark it as matched
                if opposite_order.quantity == 0:
                    opposite_order.is_matched = True
                opposite_order.save()
            
            # For IOC orders:
            if executed_quantity>0:
                # Partially executed: keep the remaining quantity
                new_order.is_matched=new_order.quantity==0
                new_order.save()
            else:
                # Completely unexecuted: delete the order
                new_order.delete()
        
        # For non-IOC orders, using existing matching logic
        else:
            remaining_quantity = new_order.quantity
            for opposite_order in opposite_orders:
                if remaining_quantity <= 0:
                    break
                
                match_quantity = min(remaining_quantity, opposite_order.quantity)
                
                # Determine trade price based on order mode
                if new_order.order_mode == 'LIMIT':
                    match_price = opposite_order.price
                else:
                    match_price = opposite_order.price
                
                # Create a trade entry for the matched orders
                Trade.objects.create(
                    buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                    seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                    quantity=match_quantity,
                    price=match_price,
                    timestamp=timezone.now()
                )
                
                # Update quantities of matched orders
                remaining_quantity -= match_quantity
                opposite_order.quantity -= match_quantity
                new_order.quantity -= match_quantity
                opposite_order.save()
                
                # If the opposite order is fully matched, mark it as matched
                if opposite_order.quantity == 0:
                    opposite_order.is_matched = True
                    opposite_order.save()
            
            # If the new order is fully or partially matched
            if new_order.quantity > 0:
                new_order.save()
            else:
                new_order.is_matched = True
                new_order.save()
            
            # Ensure the timestamp is updated
            new_order.timestamp = timezone.now()
            new_order.save()


               
                
            




