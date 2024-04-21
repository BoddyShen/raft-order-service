import requests
import os
from django.http import HttpResponse, JsonResponse

FRONTEND_SERVER_HOST = "localhost"
FRONTEND_SERVER_PORT = "8000"
ORDER_SERVER_HOST = "localhost"

def get_current_leader():
    try:
        response = requests.get(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/leader/")
        if response.status_code == 200:
            response_data = response.json()
            return  response_data['data']['leader_ID'], response_data['data']['leader_port']
        else:
            return None, None
    except Exception as e:
        return None, None

def get_latest_order_number():
    from ..models import Order

    try:
        latest_order = Order.objects.latest('order_number')
        print("latest_order:", latest_order)
        return int(latest_order.order_number)
    except Order.DoesNotExist:
        return 0

def synchronize_orders(leader_port):
    from ..models import Order
    latest_order_number = get_latest_order_number()
    next_number = latest_order_number + 1
    try:
        response = requests.post(f"http://{ORDER_SERVER_HOST}:{leader_port}/sync/order/", json={"next_number": next_number})
        if response.status_code == 200:
            orders_data = response.json()
            if 'orders' in orders_data:
                for order in orders_data['orders']:
                    Order.objects.create(
                    order_number=order['order_number'],
                    product_name=order['product_name'],
                    quantity=order['quantity']
                )
        return JsonResponse(status = 200, data = {'message': 'Synchronize orders successfully'})
    except requests.RequestException:
        return JsonResponse(status = 500, data = {"error": {"code": 500, "message": "Internal server error"}})


def set_self_as_leader(current_id):
    try:
        requests.post(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/leader/", json={"new_leader_id": current_id})
    except requests.RequestException:
        pass