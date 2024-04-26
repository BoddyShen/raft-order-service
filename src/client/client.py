import urllib3
import json
import random
import sys


def create_session_with_urllib3(frontend_host, frontend_port, order_probability=0.5, iterations=10):
    """
    Creates a session with the front-end service using urllib3, querying items and optionally placing orders.

    Parameters:
    - frontend_host (str): The hostname of the front-end service.
    - frontend_port (int): The port number of the front-end service.
    - order_probability (float): The probability of placing an order if the item quantity is greater than zero.
    - iterations (int): The number of iterations to perform.
    """
    # Create a PoolManager instance for handling connections
    retries = urllib3.util.retry.Retry(total=5, backoff_factor=1)
    http = urllib3.PoolManager(retries=retries)
    products = ["Tux", "Uno", "Clue", "Lego", "Chess", "Barbie", "Bubbles", "Frisbee", "Twister", "Elephant"]

    base_url = f"http://{frontend_host}:{frontend_port}"
    client_order_records = []

    for _ in range(iterations):
        product_name = random.choice(products)
        try:
            response = http.request("GET", f"{base_url}/products/{product_name}")
            
            if response.status == 200:
                try:
                    data = json.loads(response.data.decode('utf-8'))
                    print(f"Query {product_name}:", data)

                    if int(data['data']["quantity"]) > 0:
                        if random.random() < order_probability:
                            order_data = json.dumps(
                                {"name": product_name, "quantity": 1}).encode('utf-8')
                            order_response = http.request(
                                "POST", f"{base_url}/orders",
                                body=order_data,
                                headers={'Content-Type': 'application/json'}
                            )
                            if order_response.status == 200:
                                order_data_json = json.loads(order_response.data.decode('utf-8'))
                                order_data = {"name": product_name, "quantity": 1, "number": order_data_json['data']['order_number']}
                                client_order_records.append(order_data)
                                print(f"Order {product_name}: {order_data_json}")
                            else:
                                print(f"Failed to place order for {product_name}: {order_response.status}")
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON response for {product_name}.")
            else:
                print(f"Error querying product {product_name}: {response.status}")
        except urllib3.exceptions.HTTPError as e:
            print(f"HTTP error occurred while querying product {product_name}: {str(e)}")
        except Exception as e:
            print(f"An unexpected error occurred while querying product {product_name}: {str(e)}")

    for order_data in client_order_records:
        try:
            order_number = order_data["number"]
            response = http.request("GET", f"{base_url}/orders/{order_number}")
            if response.status == 200:
                server_data = json.loads(response.data.decode('utf-8'))
                print(f"Order in client: {order_data}, Order in server: {server_data['data']}")
                assert order_data == server_data['data']
            else:
                print(f"Failed to verify order {order_number}: {response.status}")
        except json.JSONDecodeError:
            print(f"Failed to decode JSON for order verification {order_number}.")
        except Exception as e:
            print(f"An error occurred while verifying order {order_number}: {str(e)}")

if __name__ == "__main__":
    frontend_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    frontend_port = sys.argv[2] if len(sys.argv) > 2 else "8000"
    order_probability = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    iterations = sys.argv[4] if len(sys.argv) > 4 else 10

    create_session_with_urllib3(frontend_host, 8000, order_probability, iterations)