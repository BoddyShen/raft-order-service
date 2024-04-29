import urllib3
import json
import random
import sys
import time


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
    query_latencies = []
    order_latencies = []

    for _ in range(iterations):
        product_name = random.choice(products)
        try:
            # Send a query request
            query_start_time = time.time()
            response = http.request("GET", f"{base_url}/products/{product_name}")
            query_end_time = time.time()
            query_latencies.append(query_end_time - query_start_time)

            if response.status == 200:
                try:
                    data = json.loads(response.data.decode('utf-8'))
                    print(f"Query {product_name}:", data['data'])
                    
                    if int(data['data']["quantity"]) > 0:
                        if random.random() < order_probability:
                            order_data = json.dumps(
                                {"name": product_name, "quantity": 1}).encode('utf-8')
                            
                            # Send an order request
                            order_start_time = time.time()
                            order_response = http.request(
                                "POST", f"{base_url}/orders",
                                body=order_data,
                                headers={'Content-Type': 'application/json'}
                            )
                            order_end_time = time.time()
                            order_latencies.append(order_end_time - order_start_time)

                            if order_response.status == 200:
                                order_data_json = json.loads(order_response.data.decode('utf-8'))
                                order_data = {"name": product_name, "quantity": 1, "number": order_data_json['data']['order_number']}
                                client_order_records.append(order_data)
                                print(f"Order {product_name}: {order_data_json['data']}")
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

    difference = 0
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
        except AssertionError:
            difference += 1
            print(f"Order {order_number} does not match server data")
        except Exception as e:
            print(f"An error occurred while verifying order {order_number}: {str(e)}")

    # Print out the latencies and order check results
    if query_latencies:
        print("=================\n"
            "| Query Request |\n"
            "=================\n"
            "Total number of query requests: {}\n"
            "Average Latency: {:.7f} seconds\n".format(len(query_latencies), sum(query_latencies) / len(query_latencies)))
    if order_latencies:
        print("=================\n"
            "| Order Request |\n"
            "=================\n"
            "Total number of order requests: {}\n"
            "Average Latency: {:.7f} seconds\n"
            "Total number of unmatched order: {}\n".format(len(order_latencies), sum(order_latencies) / len(order_latencies), difference))



if __name__ == "__main__":
    frontend_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    frontend_port = sys.argv[2] if len(sys.argv) > 2 else "8000"
    order_probability = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    iterations = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    create_session_with_urllib3(frontend_host, frontend_port, order_probability, iterations)