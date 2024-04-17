import json
import requests
from celery import shared_task
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET, require_POST
from .models import Product
from .utils import catalogs, ReadWriteLock


# Define the host and port for the frontend server
FRONTEND_SERVER_HOST = "localhost"
FRONTEND_SERVER_PORT = "8000"

# Create a read-write lock for accessing product data
products_lock = ReadWriteLock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()


@shared_task
def restock_product():
    for product in catalogs.values():
        try:
            # Retrieve details for every product in the catalog
            with products_lock:
                product_in_stock = Product.objects.get(name=product["name"])
            
            # Check whether each product is out of stock
            if product_in_stock.quantity <= 0:
                # Restock out-of-stock products to 100
                with products_lock:
                    product_in_stock.quantity = product["quantity"]
                    product_in_stock.save()
                
                # Send request to the frontend server to invalidate the restocked product in the cache
                requests.delete(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/cache/{product['name']}/")
                print(f"Restocked { product['name']}")
        except Product.DoesNotExist:
            # Create the product in the stock database if it does not exist
            with products_lock:
                Product.objects.create(
                    name = product["name"],
                    price = product["price"],
                    quantity = product["quantity"]
            )
        except Exception as e:
            pass


def process_get_product_request(product_name):
    try:
        # Get the product detail from the database
        with products_lock:
            product = Product.objects.get(name = product_name)
        return JsonResponse(status = 200, data = {"data": model_to_dict(product, exclude=['id'])})
    except Product.DoesNotExist:
        return JsonResponse(status = 404, data = {"error": {"code": 404, "message": "Product not found"}})
    except Exception as e:
        return JsonResponse(status = 500, data={"error": {"code": 500, "message": "Internal server error"}})


def process_post_order_request(order_data):
    try:
        with transaction.atomic():
            # Check whether the product exists
            with products_lock:
                product = Product.objects.get(name = order_data["name"])

            # Check whether the stock quantity is adequate
            if order_data["quantity"] > product.quantity:
                return JsonResponse(status=400, data={"error": {"code": 400, "message": "No sufficient stock"}})

            # Update the product quantity
            with products_lock:
                product.quantity -= order_data["quantity"]
                product.save()

                # Send request to the frontend server to invalidate the ordered product in the cache
                requests.delete(f"http://{FRONTEND_SERVER_HOST}:{FRONTEND_SERVER_PORT}/cache/{order_data['name']}/")

            # Return success response
            return JsonResponse(status=200, data={"data": {"message": "Product stock updated successfully"}})
    except Product.DoesNotExist:
        return JsonResponse(status=404, data={"error": {"code": 404, "message": "Product not found"}})
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


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
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})