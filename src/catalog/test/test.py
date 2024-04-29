import pytest
from rest_framework import status
import json
from unittest import mock
from app.models import Product
from app.views import process_get_product_request, process_post_order_request, process_post_cache_restock_request

def test_get_product_success():
    product_name = "Tux"
    catalogs_in_memory = {"Tux": {"name": "Tux", "price": 6.90, "quantity": 81}}
    expected_response = {"data": {"name": "Tux", "price": 6.90, "quantity": 81}}

    with mock.patch("app.views.catalogs_in_memory", catalogs_in_memory):
        response = process_get_product_request(product_name)

    assert response.status_code == status.HTTP_200_OK
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_get_product_success:", response.status_code, expected_response)


def test_get_product_fail():
    prodcut_name = "Tux"
    catalogs_in_memory = {}
    expected_response = {"error": {"code": 404, "message": "Product not found"}}

    with mock.patch("app.views.catalogs_in_memory", catalogs_in_memory):
        response = process_get_product_request(prodcut_name)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_get_product_fail:", response.status_code, expected_response)


@pytest.mark.django_db
def test_post_order_success():
    # Create Products in testing database.
    Product.objects.create(name="Tux", price=6.90, quantity=81)

    order_data = {"name": "Tux", "quantity": 2}
    initial_quantity = 81
    catalogs_in_memory = {"Tux": {"name": "Tux", "price": 6.90, "quantity": initial_quantity}}
    expected_response = {"data": {"message": "Product stock updated successfully"}}

    with mock.patch("app.views.catalogs_in_memory", catalogs_in_memory):
        response = process_post_order_request(order_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_post_order_success:", response.status_code, expected_response)

    product = Product.objects.get(name="Tux")
    assert product.quantity == initial_quantity - order_data["quantity"], "The product stock should be decreased by the ordered quantity."
    print("test_post_order_success:", response.status_code, response_data, "New Quantity:", product.quantity)


@pytest.mark.django_db
def test_post_order_fail():
    # Create Products in testing database.
    Product.objects.create(name="Tux", price=6.90, quantity=81)

    order_data = {"name": "Tux", "quantity": 100}
    initial_quantity = 81
    catalogs_in_memory = {"Tux": {"name": "Tux", "price": 6.90, "quantity": initial_quantity}}
    expected_response = {"error": {"code": 400, "message": "No sufficient stock"}}

    with mock.patch("app.views.catalogs_in_memory", catalogs_in_memory):
        response = process_post_order_request(order_data)

    assert response.status_code == 400
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_post_order_fail:", expected_response)


def test_post_cache_restock_success():
    initial_quantity = 0
    catalogs_in_memory = {"Tux": {"name": "Tux", "price": 6.90, "quantity": initial_quantity}}
    expected_response = {"data": {"message": f"Cache restock successfully"}}
    restock_product_data = {"product_name": "Tux", "quantity": 100}

    with mock.patch("app.views.catalogs_in_memory", catalogs_in_memory):
        response = process_post_cache_restock_request(restock_product_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_post_cache_restock_success:", response.status_code, expected_response)
    assert catalogs_in_memory["Tux"]["quantity"] == restock_product_data["quantity"]

    