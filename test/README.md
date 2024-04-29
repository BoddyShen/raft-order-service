# Test

## Load Testing

Run a script to make 5 clients sending concurrent requests to the server:

```
source venv/bin/activate
cd test
./load_test.sh <SERVER_IP> <PORT> <ORDER_PROBABILITY> <ITERATIONS>
```

If `SERVER_IP`, `PORT`, `ORDER_PROBABILITY`, and `ITERATIONS` are not specified, they are set to `0.0.0.0`, `8000`, `0.5`, and `10` as default values.