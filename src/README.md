# How to Run

## Run the Applications Using a Script
1. Check whether you are in the root directory:
    ```
    cd spring24-lab3-liangyu0516-BoddyShen/
    ```
2. Run the shell script to start all applications:
    ```
    ./build.sh
    ```
3. Run the shell script to stop all applications:
    ```
    ./stop.sh
    ```

## Run the Applications Manually
### Prerequisites
After pulling the entire repo, we first need to install all necessary packages. We will use `venv` to do so.
1. Check whether you are in the root directory:
    ```
    cd spring24-lab3-liangyu0516-BoddyShen/
    ```
2. Create a virtual environment:
    ```
    python3 -m venv venv
    ```
3. Activate the virtual environment:
    ```
    source venv/bin/activate
    ```
4. Install all the packages:
    ```
    pip install -r requirements.txt
    ```

### Front-end Service

Open a new terminal and run the followings command to start the frontend server at port `8000`. Use `USE_CACHE=True` to enable caching and `USE_CACHE=False` to disable caching:
```
source venv/bin/activate
cd src/frontend
python manage.py makemigrations && python manage.py migrate
USE_CACHE=<True or False> python manage.py runserver 8000
```

### Catalog Service

1. Open a new terminal and start Redis at port `6379` for periodic tasks:
   ```
   source venv/bin/activate
   cd src/catalog
   redis-server
   ```
2. Open a new terminal and run the following commands to start the catalog server at port `8001`:
   ```
   source venv/bin/activate
   cd src/catalog
   python manage.py makemigrations && python manage.py migrate
   python manage.py runserver 8001
   ```
3. Open another terminal and start the periodic task to restock products:
   ```
   source venv/bin/activate
   cd src/catalog
   celery -A catalog worker --loglevel=info --beat
   ```

### Order Service

1. Open a new terminal and run the following commands to start one order server replica at port `8002`:
   ```
   source venv/bin/activate
   cd src/order
   python manage.py makemigrations && DB_NAME=db1.sqlite3 python manage.py migrate
   ORDER_SERVER_ID=3 DB_NAME=db1.sqlite3 python manage.py runserver 8002
   ```
2. Open another terminal and run the following commands to start another order server replica at port `8003`:
   ```
   source venv/bin/activate
   cd src/order
   python manage.py makemigrations && DB_NAME=db2.sqlite3 python manage.py migrate
   ORDER_SERVER_ID=2 DB_NAME=db2.sqlite3 python manage.py runserver 8003
   ```
3. Open another terminal and run the following commands to start the last order server replica at port `8004`:
   ```
   source venv/bin/activate
   cd src/order
   python manage.py makemigrations && DB_NAME=db3.sqlite3 python manage.py migrate
   ORDER_SERVER_ID=1 DB_NAME=db3.sqlite3 python manage.py runserver 8004
   ```

### Client

Open a new terminal and run the following commands to make client query and order toys for several iterations:
```
source venv/bin/activate
cd src/client
python client.py [frontend_host] [frontend_port] [order_probability] [iterations]
```

If `frontend_host`, `frontend_port`, `order_probability`, and `iterations` are not specified, they are set to `localhost`, `8000`, `0.5`, and `10` as default values.

### Test

Unit testing and integration testing are both based on `pytest`, and we also employ `request_mock` to simulate responses from other microservices, thereby isolating the unit tests within each service.

Integration test is in the integration test folder, and the unit test of each services is in each service's test folder.

Before starting the tests, ensure to execute the following command:

```
export PYTHONPATH="${PYTHONPATH}:/path/to/spring24-lab3-liangyu0516-BoddyShen"
```

At the root directory, start all the servers by executing the following command:

```
./build.sh

Then run the integration tests by executing:

```

pytest integration_test/test_integration.py -v -s

```

run the unit tests:

```

pytest src/frontend -v -s
pytest src/catalog -v -s
pytest src/order -v -s

```

```
