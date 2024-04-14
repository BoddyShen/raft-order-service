# How to Run
## Prerequisites
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

## Front-end Service
Open a new terminal and run the following commands to start the frontend server at port `8000`:
```
cd src/frontend
python manage.py runserver 8000
```

## Catalog Service
1. Open a new terminal and start Redis at port `6379` for periodic tasks:
    ```
    cd src/catalog
    redis-server
    ```
2. Open another terminal and start the periodic task to restock products:
    ```
    cd src/catalog
    celery -A catalog worker --loglevel=info --beat
    ```
3. Open a new terminal and run the following commands to start the catalog server at port `8001`:
    ```
    cd src/catalog
    python manage.py makemigrations && python manage.py migrate
    python manage.py runserver 8001
    ```

## Order Service
Open a new terminal and run the following commands to start the order server at port `8002`:
```
cd src/order
python manage.py makemigrations && python manage.py migrate
python manage.py runserver 8002
```