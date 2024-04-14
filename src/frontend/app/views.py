import json
import requests
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .utils import ReadWriteLock


# Define the host and port for the catalog and order servers
CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORT = "8002"

# Create a cache to store 5 query repsonses
cache = []

# Create a read-write lock for accessing the cache
cache_lock = ReadWriteLock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()


def process_get_product_request(product_name):
    # Check whether the product is in the cache
    with cache_lock:
        for product in cache:
            if product["name"] == product_name:
                return JsonResponse(status = product["response"].status_code, data = product["response"].json())
    
    # Ask for the product detail from the catalog server
    response = requests.get(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{product_name}/")

    # Add the successful response to the cache
    if response.status_code == 200:
        with cache_lock:
            # Implement the Least Recently Used (LRU) cache replacement policy
            if len(cache) == 5:
                cache.pop(0)
            cache.append({"name": product_name, "response": response})
    
    return JsonResponse(status = response.status_code, data = response.json())


def process_get_order_request(order_number):
    # Ask for the order detail from the order server
    response = requests.get(f"http://{ORDER_SERVER_HOST}:{ORDER_SERVER_PORT}/orders/{order_number}/")
    return JsonResponse(status = response.status_code, data = response.json())


def process_post_order_request(order_data):
    # Send the buy request to the order server
    response = requests.post(f"http://{ORDER_SERVER_HOST}:{ORDER_SERVER_PORT}/orders/", json=order_data)
    return JsonResponse(status = response.status_code, data = response.json())


def process_delete_cache_request(product_name):
    # Check whether the product is in the cache
    with cache_lock:
        for i in range(len(cache)):
            if cache[i]["name"] == product_name:
                # Remove response in the cache
                cache.pop(i)
    
    # Return response indicating that the product cache invalidation was successful
    return JsonResponse(status=200, data={"data": {"message": f"Cache invalidated successfully"}})


@require_GET
def get_product(request, product_name):
    try:
        # Submit a task to the thread pool executor
        future = executor.submit(process_get_product_request, product_name)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status = 500, data = {"error": {"code": 500, "message": "Internal server error"}})


@require_GET
def get_order(request, order_number):
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


@require_http_methods(["DELETE"])
def delete_cache(request, product_name):
    try:
        # Submit a task to the thread pool executor
        future = executor.submit(process_delete_cache_request, product_name)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})