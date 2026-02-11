from django.db import transaction
from django.utils import timezone
from .models import Order, Trade
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def match_order(new_order):
    # print("match") 
    # Use closing_price to track the last trade price (not strictly needed for logic but kept for consistency)
    closing_price = None
    # Lists for bulk operations
    trades_to_create = []
    orders_to_update = []
    
    # Counter for total orders fetched
    total_orders_fetched = 0
    
    with transaction.atomic():
        # Dynamic level fetching: 20 -> 50 -> ALL
        FIRST_BATCH = 20
        SECOND_BATCH = 50
        offset = 0
        batch_number = 1
        
        # 1. Fetch opposite orders
        while True:
            # Determine fetch size based on batch number
            if batch_number == 1:
                fetch_size = FIRST_BATCH
            elif batch_number == 2:
                fetch_size = SECOND_BATCH
            else:
                fetch_size = None  # Fetch all remaining
            
            if new_order.order_type == 'BUY' and new_order.order_mode == 'LIMIT':
                query = Order.objects.select_for_update().filter(
                    order_type='SELL', 
                    order_mode='LIMIT', 
                    price__lte=new_order.price, 
                    is_matched=False
                ).order_by('price', 'timestamp')
                if fetch_size:
                    opposite_orders = list(query[offset:offset + fetch_size])
                else:
                    opposite_orders = list(query[offset:])
            
            elif new_order.order_type == 'SELL' and new_order.order_mode == 'LIMIT':
                query = Order.objects.select_for_update().filter(
                    order_type='BUY', 
                    order_mode='LIMIT', 
                    price__gte=new_order.price, 
                    is_matched=False
                ).order_by('-price', 'timestamp')
                if fetch_size:
                    opposite_orders = list(query[offset:offset + fetch_size])
                else:
                    opposite_orders = list(query[offset:])
            elif new_order.order_type == 'BUY' and new_order.order_mode == 'MARKET':
                query = Order.objects.select_for_update().filter(
                    order_type='SELL', 
                    is_matched=False
                ).order_by('price', 'timestamp')
                if fetch_size:
                    opposite_orders = list(query[offset:offset + fetch_size])
                else:
                    opposite_orders = list(query[offset:])
            elif new_order.order_type == 'SELL' and new_order.order_mode == 'MARKET':
                query = Order.objects.select_for_update().filter(
                    order_type='BUY', 
                    is_matched=False
                ).order_by('-price', 'timestamp')
                if fetch_size:
                    opposite_orders = list(query[offset:offset + fetch_size])
                else:
                    opposite_orders = list(query[offset:])
            else:
                opposite_orders = [] # Should not happen based on logic
            
            # Update counter and print
            batch_count = len(opposite_orders)
            total_orders_fetched += batch_count
            print(f"Batch {batch_number}: Fetched {batch_count} orders | Total fetched: {total_orders_fetched}")
            
            # If no more orders fetched, break
            if not opposite_orders:
                break
            
            # 2. Process IOC Orders
            if new_order.is_ioc:
                executed_quantity = 0
                
                for opposite_order in opposite_orders:
                    if new_order.quantity <= 0:
                        break
                    
                    match_quantity = min(new_order.quantity, opposite_order.quantity)
                    closing_price = opposite_order.price # IOC takes counterparty price
                    
                    # Trade record
                    trades_to_create.append(Trade(
                        buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                        seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                        quantity=match_quantity,
                        price=closing_price,
                        timestamp=timezone.now()
                    ))
                    
                    # Update quantities
                    executed_quantity += match_quantity
                    new_order.quantity -= match_quantity
                    opposite_order.quantity -= match_quantity
                    
                    # Update disclosed quantity logic (preserved from original)
                    if opposite_order.disclosed > opposite_order.quantity:
                        opposite_order.disclosed = opposite_order.quantity
                    if new_order.disclosed > new_order.quantity:
                        new_order.disclosed = new_order.quantity
                    
                    # Check matching status
                    if opposite_order.quantity == 0:
                        opposite_order.is_matched = True
                    
                    orders_to_update.append(opposite_order)
                
                # Check if order is fully matched, if yes break the while loop
                if new_order.quantity <= 0:
                    print(f"Order fully matched after fetching {total_orders_fetched} orders")
                    break
                
                # If we've fetched all (batch 3+), break
                if batch_number >= 3:
                    print(f"Reached batch 3 - fetched all available orders ({total_orders_fetched} total)")
                    break
                
                # Move to next batch
                if fetch_size:
                    offset += fetch_size
                batch_number += 1
            # 3. Process Normal User Orders (Limit/Market)
            else:
                for opposite_order in opposite_orders:
                    if new_order.quantity <= 0:
                        break
                    
                    match_quantity = min(new_order.quantity, opposite_order.quantity)
                    
                    # Price determination
                    # For LIMIT vs LIMIT, price is opposite_order.price (maker price)
                    # For MARKET, price is opposite_order.price
                    match_price = opposite_order.price
                    
                    trades_to_create.append(Trade(
                        buyer=new_order.user if new_order.order_type == 'BUY' else opposite_order.user,
                        seller=opposite_order.user if new_order.order_type == 'BUY' else new_order.user,
                        quantity=match_quantity,
                        price=match_price,
                        timestamp=timezone.now()
                    ))
                    
                    # Update quantities
                    opposite_order.quantity -= match_quantity
                    new_order.quantity -= match_quantity
                    
                    if opposite_order.disclosed > opposite_order.quantity:
                        opposite_order.disclosed = opposite_order.quantity
                    if new_order.disclosed > new_order.quantity:
                        new_order.disclosed = new_order.quantity
                    
                    if opposite_order.quantity == 0:
                        opposite_order.is_matched = True
                    
                    orders_to_update.append(opposite_order)
                
                # Check if order is fully matched, if yes break the while loop
                if new_order.quantity <= 0:
                    print(f"Order fully matched after fetching {total_orders_fetched} orders")
                    break
                
                # If we've fetched all (batch 3+), break
                if batch_number >= 3:
                    print(f"Reached batch 3 - fetched all available orders ({total_orders_fetched} total)")
                    break
                
                # Move to next batch
                if fetch_size:
                    offset += fetch_size
                batch_number += 1
        
        # Post-matching IOC logic (moved outside the while loop)
        if new_order.is_ioc:
            executed_quantity = sum(t.quantity for t in trades_to_create if (t.buyer == new_order.user and new_order.order_type == 'BUY') or (t.seller == new_order.user and new_order.order_type == 'SELL'))
            
            if executed_quantity > 0:
                # Partially or fully executed
                new_order.quantity = 0 # IOC remainder is cancelled
                new_order.is_matched = True
                new_order.disclosed = 0
                # Don't save yet, will be handled below
            else:
                # Completely unexecuted - delete after transaction
                new_order.delete()
                # If deleted, we return early. 
                # But we still need to save trade/updates if any (though executed_quantity is 0 here)
                # If executed_quantity is 0, nothing in trades_to_create/orders_to_update
                broadcast_orderbook_update()
                return
        else:
            # Market order special handling
            if new_order.order_mode == 'MARKET' and new_order.quantity > 0:
                # Unfilled market orders are cancelled
                new_order.quantity = 0
                new_order.is_matched = True
            elif new_order.quantity == 0:
                new_order.is_matched = True
            
            new_order.timestamp = timezone.now()
        
        # 4. Perform Bulk DB Operations
        print(f"Creating {len(trades_to_create)} trades and updating {len(orders_to_update)} orders")
        
        if trades_to_create:
            Trade.objects.bulk_create(trades_to_create)
        
        if orders_to_update:
            # Only update fields that changed
            Order.objects.bulk_update(orders_to_update, ['quantity', 'is_matched', 'disclosed'])
        # Save new_order if not deleted
        if new_order.pk:  # Check if not deleted
            new_order.save()
            
    # 5. Single Broadcast at the end
    broadcast_orderbook_update()

def broadcast_orderbook_update():
    
    # OPTIMIZATION: Limit to top 20 orders instead of fetching all
    buy_orders = Order.objects.filter(order_type='BUY', is_matched=False).order_by('-price')[:20]
    sell_orders = Order.objects.filter(order_type='SELL', is_matched=False).order_by('price')[:20]
    recent_trades = Trade.objects.order_by('-timestamp')[:10]
    best_bid = buy_orders[0] if buy_orders else None
    best_ask = sell_orders[0] if sell_orders else None
    # Need to evaluate QuerySets to list to serialize
    buy_orders_list = list(buy_orders)
    sell_orders_list = list(sell_orders)
    recent_trades_list = list(recent_trades)
    payload = {
        'best_bid': {
            'price': float(best_bid.price),
            'disclosed': best_bid.disclosed,
        } if best_bid else None,
        'best_ask': {
            'price': float(best_ask.price),
            'disclosed': best_ask.disclosed,
        } if best_ask else None,
        'buy_orders': [
            {
                'price': float(o.price),
                'disclosed': o.disclosed,
            } for o in buy_orders_list
        ],
        'sell_orders': [
            {
                'price': float(o.price),
                'disclosed': o.disclosed,
            } for o in sell_orders_list
        ],
        'trades': [
            {
                'buyer': t.buyer.username,
                'seller': t.seller.username,
                'price': float(t.price),
                'quantity': t.quantity,
                'timestamp': t.timestamp.isoformat(),
            } for t in recent_trades_list
        ]
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'orderbook_group',
        {
            'type': 'send_order_update',
            'payload': payload,
        }
    )
    # print("Orderbook updated and broadcasted")
