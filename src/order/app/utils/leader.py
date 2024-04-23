import requests
import os
from django.http import HttpResponse, JsonResponse


FRONTEND_SERVER_HOST = "localhost"
FRONTEND_SERVER_PORT = "8000"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORTS = {
    "3": "8002",
    "2": "8003",
    "1": "8004",
}
ORDER_SERVER_ID = os.getenv("ORDER_SERVER_ID")

def get_current_leader():
    try:
        response = requests.get(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/leaders/")
        if response.status_code == 200:
            response_data = response.json()
            print(response_data['data']['leader_ID'], response_data['data']['leader_port'])
            return response_data['data']['leader_ID'], response_data['data']['leader_port']
        else:
            return None, None
    except Exception as e:
        return None, None

def get_latest_order_number():
    from ..models import Order
    from ..views import orders_lock
    try:
        with orders_lock:
            latest_order = Order.objects.latest('order_number')
        print("latest_order:", latest_order)
        return int(latest_order.order_number)
    except Order.DoesNotExist:
        return 0

def synchronize_orders():
    from ..models import Order
    from ..views import orders_lock
    latest_order_number = get_latest_order_number()
    next_order_number = latest_order_number + 1
    for id, port in ORDER_SERVER_PORTS.items():
        if id != ORDER_SERVER_ID:
            try:
                sync_orders_response = requests.get(f"http://{ORDER_SERVER_HOST}:{port}/sync/orders/{next_order_number}")
                if sync_orders_response.status_code == 200:
                    orders_data = sync_orders_response.json()
                    for order in orders_data["data"]["orders"]:
                        with orders_lock:
                            Order.objects.create(
                                order_number=order['order_number'],
                                product_name=order['product_name'],
                                quantity=order['quantity']
                        )
                    return JsonResponse(status = 200, data = {'message': 'Orders synchronized successfully'})
                else:
                    return JsonResponse(status = sync_orders_response.status_code, data = sync_orders_response.json())
            except Exception as e:
                continue 
    return