# Test

## Integration Testing

Unit testing and integration testing are both based on `pytest`, and we also employ `request_mock` to simulate responses from other microservices, thereby isolating the unit tests within each service.

Before starting the tests, ensure to execute the following command:

```
export PYTHONPATH="${PYTHONPATH}:/path/to/spring24-lab3-liangyu0516-BoddyShen"
```

This command ensures that Python can locate and import modules or packages located in the directory `/path/to/spring24-lab3-liangyu0516-BoddyShen`.

### Integration Testing

At the root directory, start all the servers by executing the following command:

```
./build.sh

Then run the integration tests by executing:

```

pytest integration_test/test_integration.py -v -s

```

```
