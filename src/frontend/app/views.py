import os
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .utils import ReadWriteLock
import time
import threading


# Define whether to use cache
USE_CACHE = True if os.environ.get("USE_CACHE") == "True" else False

# Define the host and port for the catalog and order servers
CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORTS = {
    "3": "8002",
    "2": "8003",
    "1": "8004",
}
order_leader_ID=None
order_leader_port=None

# Get the logger instance for the current module
logger = logging.getLogger(__name__)

# Create a cache to store 5 query repsonses
cache = []

# Create a read-write lock for accessing the cache
cache_lock = ReadWriteLock()

# Create a lock for leader
leader_lock = threading.Lock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()


def find_order_leader(max_attempts=3):
    '''
    This function is executed when there is no leader found, and the max_attempts is used for timeout control.
    '''
    global order_leader_ID, order_leader_port
    i = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            # Send a health check request to the order replica server to verify its responsiveness
            health_check_response = requests.get(f"http://{ORDER_SERVER_HOST}:{ORDER_SERVER_PORTS[str(i)]}/")
            
            # Set the ID and the port of the leader order server
            with leader_lock:
                order_leader_ID = str(i)
                order_leader_port = ORDER_SERVER_PORTS[str(i)]
            logger.info(f"Order leader ID: {order_leader_ID}, order leader port: {order_leader_port}")

            leader_data = {"leader_id": order_leader_ID}
            for id, port in ORDER_SERVER_PORTS.items():
                if id is not order_leader_ID:
                    try:
                        # Inform other order server replicas about the leader ID
                        leader_response = requests.post(f"http://{ORDER_SERVER_HOST}:{port}/replicas/leaders/", json=leader_data)
                    except:
                        pass
                        
            return order_leader_ID
        except:
            # Update the next checking ID
            if i == 1: 
                logger.info("Temporary not find available order server, retrying in 3 seconds...")
                time.sleep(3)
                attempts += 1
                i = 3
            else: i -= 1
    
    return 
            

def process_get_product_request(product_name):
    global USE_CACHE, cache
    if USE_CACHE:
        # Check whether the product is in the cache
        with cache_lock:
            for i in range(len(cache)):
                if cache[i]["name"] == product_name:
                    cache_response = cache[i]["response"]
                    cache.pop(i)
                    cache.append({"name": product_name, "response": cache_response})
                    return JsonResponse(status = cache_response.status_code, data = cache_response.json())
    
    # Ask for the product detail from the catalog server
    response = requests.get(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{product_name}/")

    # Add the successful response to the cache
    if response.status_code == 200:
        if USE_CACHE:
            with cache_lock:
                # Implement the Least Recently Used (LRU) cache replacement policy
                if len(cache) == 5:
                    cache.pop(0)
                cache.append({"name": product_name, "response": response})
    return JsonResponse(status = response.status_code, data = response.json())


def process_get_order_request(order_number):
    # Ask for the order detail from the order server
    response = requests.get(f"http://{ORDER_SERVER_HOST}:{order_leader_port}/orders/{order_number}/")
    return JsonResponse(status = response.status_code, data = response.json())

def process_post_order_request(order_data):
    # Send the buy request to the order server
    response = requests.post(f"http://{ORDER_SERVER_HOST}:{order_leader_port}/orders/", json=order_data)
    return JsonResponse(status = response.status_code, data = response.json())


def process_delete_cache_request(product_name):
    global USE_CACHE
    if USE_CACHE:
        # Check whether the product is in the cache
        with cache_lock:
            for i in range(len(cache)):
                if cache[i]["name"] == product_name:
                    # Remove response in the cache
                    cache.pop(i)
    
    # Return response indicating that the product cache invalidation was successful
    return JsonResponse(status=200, data={"data": {"message": f"Cache invalidated successfully"}})


def process_get_leader_request():
    global order_leader_ID, order_leader_port
    if order_leader_ID and order_leader_port:
        return JsonResponse(status=200, data={"data": {"leader_ID": order_leader_ID, "leader_port": order_leader_port}})
    else:
        return JsonResponse(status=404, data={"error": {"code": 404, "message": "Leader not found"}})


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
        logger.info("Error connecting to leader. Re-electing...")

        leader = find_order_leader()
        if leader:
            logger.info(f'''Current leader switched to ID: {leader}''')
            try:
                future = executor.submit(process_get_order_request, order_number)
                response = future.result()
                return response
            except:
                pass  
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
        logger.info("Error connecting to leader. Re-electing...")
        # print("Error connecting to leader. Re-electing...")

        leader = find_order_leader()
        if leader:
            logger.info(f'''Current leader switched to ID: {leader}''')
            try:
                future = executor.submit(process_post_order_request, order_data)
                response = future.result()
                return response
            except:
                pass  
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
    

@require_GET
def get_leader(request):
    try:
        # Submit a task to the thread pool executor
        future = executor.submit(process_get_leader_request)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status = 500, data = {"error": {"code": 500, "message": "Internal server error"}})