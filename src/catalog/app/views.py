import json
import requests
from celery import shared_task
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import Product
from .utils import catalogs, ReadWriteLock
from urllib.parse import parse_qs, parse_qsl


# Define the host and port for the frontend server
FRONTEND_SERVER_HOST = "localhost"
FRONTEND_SERVER_PORT = "8000"
CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"

# Create a read-write lock for accessing on-disk and in-memory product data
products_lock = ReadWriteLock()
catalogs_lock = ReadWriteLock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()

# Create in memory
catalogs_in_memory = dict()


@shared_task
def restock_product():
    global catalogs_in_memory
    for product in catalogs.values():
        try:
            # Retrieve details for every product in the catalog
            with products_lock:
                product_in_db = Product.objects.get(name=product["name"])
            with catalogs_lock:
                product_in_memory = catalogs_in_memory.get(product["name"], None)
            print(product_in_db)
            if not product_in_memory:
                with catalogs_lock:
                    catalogs_in_memory[product["name"]] = {
                        "name": product_in_db.name,
                        "price": product_in_db.price,
                        "quantity": product_in_db.quantity
                    }
            product_in_db = Product.objects.get(name=product["name"])
            print("product_in_db", product_in_db)
            
            # Check whether each product is out of stock
            if product_in_db.quantity <= 0:
                # Restock out-of-stock products to 100
                with products_lock:
                    product_in_db.quantity = product["quantity"]
                    product_in_db.save()
                with catalogs_lock:
                    print(catalogs_in_memory[product["name"]])
                    catalogs_in_memory[product["name"]]["quantity"] = product["quantity"]
                    print(catalogs_in_memory[product["name"]])
                
                # Send request to the frontend server to invalidate the restocked product in the cache
                product_in_db.quantity = product["quantity"]
                product_in_db.save()

                # Send request to the frontend and catalog server to invalidate the restocked product in the cache
                requests.delete(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/cache/{product['name']}/")
                # Send request to restock the product in the cache
                url = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/cache/restock/"
                headers = {'Content-Type': 'application/json'}
                payload = {"product_name": "Tux", "quantity": 100}
                 
                requests.post(url, headers=headers, json=payload)
                # requests.post(url, json={'product_name': 'Tux', 'quantity': 100})
                print(f"Restocked { product['name']}")
        except Product.DoesNotExist:
            # Create the product in the stock database if it does not exist
            with products_lock:
                Product.objects.create(
                    name = product["name"],
                    price = product["price"],
                    quantity = product["quantity"]
            )
            with catalogs_lock:
                catalogs_in_memory[product["name"]] = {
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": product["quantity"]
                }
        except Exception as e:
            pass


def process_get_product_request(product_name):
    global catalogs_in_memory
    try:
        # Get the product detail from the database
        with catalogs_lock:
            product = catalogs_in_memory.get(product_name, None)
            if product:
                return JsonResponse(status = 200, data = {"data": product})
            else:
                return JsonResponse(status = 404, data = {"error": {"code": 404, "message": "Product not found"}})
    except Exception as e:
        return JsonResponse(status = 500, data={"error": {"code": 500, "message": "Internal server error"}})


def process_post_order_request(order_data):
    global catalogs_in_memory
    try:
        with transaction.atomic():
            # Check whether the product exists
            with catalogs_lock:
                product_in_memory = catalogs_in_memory.get(order_data["name"], None)

            # Check whether the stock quantity is adequate
            if order_data["quantity"] > product_in_memory["quantity"]:
                return JsonResponse(status=400, data={"error": {"code": 400, "message": "No sufficient stock"}})

            # Update the product quantity
            with catalogs_lock:
                catalogs_in_memory[order_data["name"]]["quantity"] -= order_data["quantity"]
            with products_lock:
                product_in_db = Product.objects.get(name = order_data["name"])
                product_in_db.quantity -= order_data["quantity"]
                product_in_db.save()

            # Send request to the frontend server to invalidate the ordered product in the cache
            requests.delete(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/cache/{order_data['name']}/")

            # Return success response
            return JsonResponse(status=200, data={"data": {"message": "Product stock updated successfully"}})
    except Product.DoesNotExist:
        return JsonResponse(status=404, data={"error": {"code": 404, "message": "Product not found"}})
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})

def process_post_cache_restock_request(product_data):
    if "product_name" in product_data and "quantity" in product_data:
        product_name = product_data["product_name"]
        quantity = product_data["quantity"]
        if product_name in catalogs_in_memory:
            with catalogs_lock:
                catalogs_in_memory[product_name]["quantity"] = quantity

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
        print(e)
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})

@require_POST
def post_cache_restock(request):
    try:
        # TODO: figure out why requests in restock here can't be a json data
        restock_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_cache_restock_request, restock_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        print(e)
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    