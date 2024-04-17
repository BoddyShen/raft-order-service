import json
import requests
from concurrent.futures import ThreadPoolExecutor
from django.http import HttpResponse, JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET, require_POST
from .models import Order
from .utils import ReadWriteLock


# Define the host and port for the catalog server
CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORTS = {
    "3": "8002",
    "2": "8003",
    "1": "8004",
}
ORDER_LEADER_ID="3"
ORDER_LEADER_PORT="8002"

# Create a read-write lock for accessing order data
orders_lock = ReadWriteLock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()
    

def process_get_order_request(order_number):
    try:
        # Get the order detail from the database
        with orders_lock:
            order = Order.objects.get(order_number=order_number)
        response = {
            "number": order.order_number,
            "name": order.product_name,
            "quantity": order.quantity
        }
        return JsonResponse(status=200, data={"data": response})
    except Order.DoesNotExist:
        return JsonResponse(status=404, data={"error": {"code": 404, "message": "Order not found"}})
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


def process_post_order_request(order_data):
    # Ask for the product detail from the catalog server
    product_response = requests.get(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{order_data['name']}/")
    if product_response.status_code == 200:
        # Check whether the stock quantity is adequate
        if order_data["quantity"] > product_response.json()["data"]["quantity"]:
            return JsonResponse(status=400, data={"error": {"code": 400, "message": "No sufficient stock"}})
    if product_response.status_code == 404:
        return JsonResponse(status = 404, data = {"error": {"code": 404, "message": "Product not found"}})
    
    # Send the order request to the catalog server
    order_response = requests.post(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/orders/", json=order_data)
    if order_response.status_code == 200:
        # Create the order log
        with orders_lock:
            order = Order.objects.create(
                product_name=order_data["name"],
                quantity=order_data["quantity"]
            )

        # Send order data to other replicas for synchronizing order log
        for id, port in ORDER_SERVER_PORTS.items():
            if id is not ORDER_LEADER_ID:
                try:
                    replica_order_response = requests.post(f"http://{ORDER_SERVER_HOST}:{port}/replicas/order/", json=order_data)
                except Exception as e:
                    pass
        return JsonResponse(status=200, data={"data": model_to_dict(order, exclude=['product_name', 'quantity'])})
    else:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


def process_post_replicas_leader_request(leader_data):
    global ORDER_LEADER_ID, ORDER_LEADER_PORT
    try:
        # Set the ID and the port of the leader order server
        ORDER_LEADER_ID = leader_data["leader_id"]
        ORDER_LEADER_PORT = ORDER_SERVER_PORTS[ORDER_LEADER_ID]
        return HttpResponse(status=204)
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    

def process_post_replicas_order_request(order_data):
    try:
        # Create the order log
        with orders_lock:
            order = Order.objects.create(
                product_name=order_data["name"],
                quantity=order_data["quantity"]
            )
        return HttpResponse(status=204)
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_GET
def get_order(request, order_number):
    print(ORDER_LEADER_ID, ORDER_LEADER_PORT)
    try:
        # Submit a task to the thread pool executor
        future = executor.submit(process_get_order_request, order_number)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_POST
def post_order(request):
    try:
        # Extract data from the request
        order_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_order_request, order_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_POST
def post_replicas_leader(request):
    try:
        # Extract data from the request
        leader_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_replicas_leader_request, leader_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    

@require_POST
def post_replicas_order(request):
    try:
        # Extract data from the request
        order_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_replicas_order_request, order_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})