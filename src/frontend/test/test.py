import requests_mock
from rest_framework import status
from rest_framework.test import APIClient
import json
from unittest import mock
from django.http import JsonResponse
from app.views import process_get_product_request, process_get_order_request, process_post_order_request, process_delete_cache_request

CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORTS = {
    "3": "8002",
    "2": "8003",
    "1": "8004",
}

def test_query_product_success():
    client = APIClient()
    product_name = "Tux"
    expected_response = {"name": "Tux", "price": 15.99, "quantity": 100}
    url = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{product_name}/"
    with requests_mock.Mocker() as m:
        m.get(url, json=expected_response, status_code=200)
        response = client.get(url, kwargs={'product_name': product_name})

    assert response.status_code == 200
    assert response.json() == expected_response
    print("test_query_product_success:", response.status_code, response.json())

def test_query_product_fail():
    client = APIClient()
    product_name = "NonexistentProduct"
    expected_response = {"error": {"code": 404, "message": "Product not found"}}
    url = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{product_name}/"

    with requests_mock.Mocker() as m:
        m.get(url, json={"error": {"code": 404, "message": "Product not found"}}, status_code=404)
        response = client.get(url, kwargs={'product_name': product_name})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_data = json.loads(response.content.decode('utf-8'))
    assert response_data == expected_response
    print("test_query_product_fail:", response.status_code, expected_response)

def test_query_wrong_url():
    client = APIClient()
    response = client.get('/wrong_url')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    print("test_query_wrong_url:", response.status_code)


def test_query_order_success():
    order_number = 1
    order_leader_port = ORDER_SERVER_PORTS["1"]
    expected_response = {"number": 1, "name": "Tux", "quantity": 80}

    with mock.patch("app.views.order_leader_port", order_leader_port):
        with requests_mock.Mocker() as m:
            m.get(f"http://{ORDER_SERVER_HOST}:{order_leader_port}/orders/{order_number}/", json={"number": 1, "name": "Tux", "quantity": 80}, status_code=200)
            response = process_get_order_request(order_number)

    assert response.status_code == status.HTTP_200_OK
    response_data = json.loads(response.content.decode('utf-8'))
    assert response_data == expected_response
    print("test_query_order_success:", response.status_code, expected_response)

def test_query_order_fail():
    order_number = 10
    order_leader_port = ORDER_SERVER_PORTS["1"]
    expected_response = {"code": 404, "message": "Order not found"}

    with mock.patch("app.views.order_leader_port", order_leader_port):
        with requests_mock.Mocker() as m:
            m.get(f"http://{ORDER_SERVER_HOST}:{order_leader_port}/orders/{order_number}/", json=expected_response, status_code=404)
            response = process_get_order_request(order_number)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_data = json.loads(response.content.decode('utf-8'))
    assert response_data == expected_response
    print("test_query_order_fail:", response.status_code, expected_response)


def test_post_order_success():
    order_leader_port = ORDER_SERVER_PORTS["1"]
    order_data = {"name": "Tux", "quantity": 2}
    expected_response = {"data": {"order_number": 120}}

    with mock.patch("app.views.order_leader_port", order_leader_port):
        with requests_mock.Mocker() as m:
            m.post(f"http://{ORDER_SERVER_HOST}:{order_leader_port}/orders/", json=expected_response, status_code=200)
            response = process_post_order_request(order_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = json.loads(response.content.decode('utf-8'))
    assert response_data == expected_response
    print("test_post_order_success:", response.status_code, expected_response)

def test_delete_cache_success():
    USE_CACHE = True
    product_name = 'Tux'
    cache = [{'name': 'Tux', 'response': JsonResponse(status=200, data={"name": "Tux", "price": 15.99, "quantity": 100})}]

    with mock.patch("app.views.USE_CACHE", USE_CACHE):
        with mock.patch("app.views.cache", cache):
            response = process_delete_cache_request(product_name)

    assert response.status_code == status.HTTP_200_OK
    assert cache == []
    print("test_delete_cache_success:", response.status_code)



