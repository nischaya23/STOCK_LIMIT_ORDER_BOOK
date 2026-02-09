
import os
import django
import time
import random
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trading_system.settings")
django.setup()

from trading.models import User, Order
from trading.utils import match_order

def create_users(n=10):
    users = []
    for i in range(n):
        u, created = User.objects.get_or_create(username=f"bench_user_{i}")
        users.append(u)
    return users

def worker(user, order_type, price):
    order = Order.objects.create(
        user=user,
        order_type=order_type,
        order_mode='LIMIT',
        quantity=1,
        price=price,
        disclosed=1
    )
    # The view usually calls match_order. We call it directly to test core logic.
    match_order(order)

def run_benchmark(num_orders=100):
    print("Preparing benchmark...")
    User.objects.all().delete()
    Order.objects.all().delete()
    users = create_users(10)
    
    print(f"Starting benchmark with {num_orders} orders...")
    start_time = time.time()
    
    # Mix of buy and sell to trigger matching
    orders_to_place = []
    for i in range(num_orders):
        user = random.choice(users)
        order_type = 'BUY' if i % 2 == 0 else 'SELL'
        price = 100 + random.randint(-5, 5) # Trigger matches
        orders_to_place.append((user, order_type, price))
        
    for user, order_type, price in orders_to_place:
        worker(user, order_type, price)
        
    end_time = time.time()
    duration = end_time - start_time
    tps = num_orders / duration
    
    print(f"Placed {num_orders} orders in {duration:.2f} seconds.")
    print(f"Throughput: {tps:.2f} orders/second")

if __name__ == "__main__":
    run_benchmark(100)
