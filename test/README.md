# Test

## Load Testing

Run a script to make 5 clients sending concurrent requests to the server:

```
source venv/bin/activate
cd test
./load_test.sh <SERVER_IP> <PORT> <ORDER_PROBABILITY> <ITERATIONS>
```

If `SERVER_IP`, `PORT`, `ORDER_PROBABILITY`, and `ITERATIONS` are not specified, they are set to `0.0.0.0`, `8000`, `0.5`, and `10` as default values.

## Unit Testing and Integration Testing

Unit testing and integration testing are both based on `pytest`, and we also employ `request_mock` to simulate responses from other microservices, thereby isolating the unit tests within each service.

The integration test is located in the root `test` folder, while the unit test for each service resides in its respective service's `test` folder.

Before starting the tests, ensure to execute the following command:
```
export PYTHONPATH="${PYTHONPATH}:/path/to/spring24-lab3-liangyu0516-BoddyShen"
```

At the root directory, start all the servers by executing the following command:
```
./build.sh
```

Run the integration tests by executing the following command in the root directory:
```
source venv/bin/activate
pytest test/test_integration.py -v -s
```

In the same terminal and virtual environment, run the unit tests by executing the following commands:
```
pytest src/frontend -v -s
pytest src/catalog -v -s
pytest src/order -v -s
```