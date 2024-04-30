import requests

BASE_URL = 'http://localhost:8000'


def test_query_product_exists():
    product_name = "Tux"
    response = requests.get(f'{BASE_URL}/products/{product_name}/')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['name'] == product_name
    print("\nTest case: query_product_exists")
    print(
        f'''Response: {response.json()}''')


def test_query_without_product_name():
    product_name = ""
    response = requests.get(f'{BASE_URL}/products/{product_name}/')
    assert response.status_code == 404
    print("\nTest case: query_without_product_name")
    print("response", response)
    

def test_query_product_not_exists():
    product_name = "NonexistentProduct"
    response = requests.get(f'{BASE_URL}/products/{product_name}/')
    assert response.status_code == 404
    print("\nTest case: query_product_not_exists")
    print("response", response)


def test_query_with_wrong_url():
    product_name = "NonexistentProduct"
    response = requests.get(f'{BASE_URL}/wrong_url/{product_name}/')
    assert response.status_code == 404
    print("\nTest case: query_with_wrong_url")
    print("response", response)


def test_place_order_success():
    product_name = "Tux"
    quantity = 1
    response = requests.post(
        f'{BASE_URL}/orders/', json={"name": product_name, "quantity": quantity})
    assert response.status_code == 200
    data = response.json()
    assert "order_number" in data['data']
    print("\nTest case: place_order_success")
    print(
        f'''Response: {response.json()}''')


def test_place_order_insufficient_stock():
    product_name = "Tux"
    quantity = 10000
    response = requests.post(
        f'{BASE_URL}/orders/', json={"name": product_name, "quantity": quantity})
    assert response.status_code == 400
    print("\nTest case: place_order_insufficient_stock")
    print("response", response)


def test_place_order_product_not_exists():
    product_name = "NonexistentProduct"
    quantity = 1
    response = requests.post(
        f'{BASE_URL}/orders/', json={"name": product_name, "quantity": quantity})
    assert response.status_code == 404
    assert "error" in response.json()
    print("\nTest case: place_order_product_not_exists")
    print(
        f'''Response: {response.json()}''')


def test_place_order_with_wrong_url():
    product_name = "NonexistentProduct"
    quantity = 1
    response = requests.post(
        f'{BASE_URL}/wrong_url/', json={"name": product_name, "quantity": quantity})
    assert response.status_code == 404
    print("\nTest case: place_order_with_wrong_url")
    print("response", response)