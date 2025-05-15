from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Order, Trade

def serialize_order(order):
    return {
        "id": order.id,
        "user": order.user.username,
        "order_type": order.order_type,
        "order_mode": order.order_mode,
        "quantity": order.quantity,
        "disclosed": order.disclosed,
        "price": float(order.price) if order.price else None,
        "timestamp": order.timestamp.isoformat(),
    }

def serialize_trade(trade):
    return {
        "id": trade.id,
        "buyer": trade.buyer.username,
        "seller": trade.seller.username,
        "quantity": trade.quantity,
        "price": float(trade.price),
        "timestamp": trade.timestamp.isoformat(),
    }

def broadcast_orderbook():
    channel_layer = get_channel_layer()

    buy_orders = Order.objects.filter(order_type='BUY', is_matched=False).order_by('-price', 'timestamp')[:10]
    sell_orders = Order.objects.filter(order_type='SELL', is_matched=False).order_by('price', 'timestamp')[:10]
    recent_trades = Trade.objects.all().order_by('-timestamp')[:10]

    best_bid = buy_orders.first()
    best_ask = sell_orders.first()

    buy_orders_data = [serialize_order(o) for o in buy_orders]
    sell_orders_data = [serialize_order(o) for o in sell_orders]
    trades_data = [serialize_trade(t) for t in recent_trades]

    best_bid_data = {
        'price': float(best_bid.price) if best_bid else None,
        'disclosed': best_bid.disclosed if best_bid else None,
    }

    best_ask_data = {
        'price': float(best_ask.price) if best_ask else None,
        'disclosed': best_ask.disclosed if best_ask else None,
    }

    async_to_sync(channel_layer.group_send)(
        "orderbook_group",
        {
            "type": "orderbook_update",  # This must match the consumer method name below
            "data": {
                "buy_orders": buy_orders_data,
                "sell_orders": sell_orders_data,
                "trades": trades_data,
                "best_bid": best_bid_data,
                "best_ask": best_ask_data,
            }
        }
    )

