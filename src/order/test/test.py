import pytest
from rest_framework import status
import requests_mock
import json
from django.http import JsonResponse
from unittest import mock
from app.models import Order
from app.views import process_get_order_request, process_post_order_request, process_post_replicas_order_request, process_get_sync_orders_request

CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"

@pytest.mark.django_db
def test_get_order_success():
    for _ in range(3):
        Order.objects.create(product_name="Tux", quantity=2)
    order_number_1 = 1
    order_number_2 = 2

    expected_response_1 = {'data': {'name': 'Tux', 'number': 1, 'quantity': 2}}
    expected_response_2 = {'data': {'name': 'Tux', 'number': 2, 'quantity': 2}}

    response_1 = process_get_order_request(order_number_1)
    response_2 = process_get_order_request(order_number_2)

    assert response_1.status_code == status.HTTP_200_OK
    assert response_2.status_code == status.HTTP_200_OK

    response_1_data = json.loads(response_1.content.decode("utf-8"))
    response_2_data = json.loads(response_2.content.decode("utf-8"))

    assert response_1_data == expected_response_1
    print("test_get_order_success:", response_1.status_code, expected_response_1)
    assert response_2_data == expected_response_2
    print("test_get_order_success:", response_2.status_code, expected_response_2)


@pytest.mark.django_db
def test_get_order_fail():
    for _ in range(3):
        Order.objects.create(product_name="Tux", quantity=2)
    order_number = 10
    expected_response = {'error': {'code': 404, 'message': 'Order not found'}}
    response = process_get_order_request(order_number)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_response
    print("test_get_order_fail:", response.status_code, expected_response)


@pytest.mark.django_db
def test_post_order_success():

    order_data = {'name': 'Tux', 'quantity': 2}
    expected_response1 = JsonResponse(status = 200, data = {'data': {'name': 'Tux', 'price': '6.90', 'quantity': 77}})
    expected_response2 = JsonResponse(status = 200, data = {})

    url1 = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{order_data['name']}/"
    url2 = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/orders/"
    with requests_mock.Mocker() as m:
        m.get(url1, json=expected_response1, status_code=200)
        m.post(url2, json=expected_response2, status_code=200)

    response = process_post_order_request(order_data)
    assert response.status_code == status.HTTP_200_OK

    latest_order = Order.objects.latest('order_number')
    assert latest_order.product_name == order_data['name']
    assert latest_order.quantity == order_data['quantity']

    print("test_post_order_success", response.status_code)


@pytest.mark.django_db
def test_post_order_fail():

    order_data = {'name': 'Tux', 'quantity': 100}
    expected_response1 = JsonResponse(status = 200, data = {'data': {'name': 'Tux', 'price': '6.90', 'quantity': 77}})

    url1 = f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{order_data['name']}/"
    with requests_mock.Mocker() as m:
        m.get(url1, json=expected_response1, status_code=200)

    response = process_post_order_request(order_data)
    assert response.status_code == 400
    response_data = json.loads(response.content.decode("utf-8"))
    print("test_post_order_fail", response.status_code, response_data)


@pytest.mark.django_db
def test_post_replicas_order_success():

    order_data = {'name': 'Tux', 'quantity': 2}

    response = process_post_replicas_order_request(order_data)
    assert response.status_code == 204

    latest_order = Order.objects.latest('order_number')
    assert latest_order.product_name == order_data['name']
    assert latest_order.quantity == order_data['quantity']

    print("test_post_replicas_order_success", response.status_code)


@pytest.mark.django_db
def test_get_sync_orders_success():
    next_order_number = 2
    expected_data = {'data': {'orders': [{'order_number': 2, 'product_name': 'Tux', 'quantity': 2}, {'order_number': 3, 'product_name': 'Tux', 'quantity': 3}, {'order_number': 4, 'product_name': 'Tux', 'quantity': 4}, {'order_number': 5, 'product_name': 'Tux', 'quantity': 5}]}}

    for i in range(5):
        Order.objects.create(product_name="Tux", quantity=i+1)


    response = process_get_sync_orders_request(next_order_number)
    assert response.status_code == 200
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == expected_data
    print("test_get_sync_orders_success", response.status_code)

