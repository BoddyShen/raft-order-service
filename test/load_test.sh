#!/bin/bash

SERVER_IP=${1:-"0.0.0.0"}
PORT=${2:-"8000"}
ORDER_PROB=${3:-"0.5"}
ITERATIONS=${4:-"10"}

# Start clients in the background
for ((i=0; i<5; i++))
do
    python ../src/client/client.py $SERVER_IP $PORT $ORDER_PROB $ITERATIONS &
done

wait