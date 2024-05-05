import json
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor
from django.http import HttpResponse, JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from .models import Order, LogEntry
from .utils.locks import ReadWriteLock
from .utils.leader import get_current_leader
from .utils.raft import Raft, RaftConfig


# Define the host and port for the catalog server
CATALOG_SERVER_HOST = "localhost"
CATALOG_SERVER_PORT = "8001"
ORDER_SERVER_HOST = "localhost"
ORDER_SERVER_PORTS = {
    "3": "8002",
    "2": "8003",
    "1": "8004",
}
order_leader_ID, order_leader_port = get_current_leader()

# Create a read-write lock for accessing order data
orders_lock = ReadWriteLock()

# Create a thread pool executor for concurrent task execution
executor = ThreadPoolExecutor()
    

def process_get_order_request(order_number):
    try:
        # Get the order detail from the database
        with orders_lock:
            order = Order.objects.get(order_number=order_number)
        response = {
            "number": order.order_number,
            "name": order.product_name,
            "quantity": order.quantity
        }
        return JsonResponse(status=200, data={"data": response})
    except Order.DoesNotExist:
        return JsonResponse(status=404, data={"error": {"code": 404, "message": "Order not found"}})
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


def process_post_order_request(order_data):
    # Ask for the product detail from the catalog server
    product_response = requests.get(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/products/{order_data['name']}/")
    if product_response.status_code == 200:
        # Check whether the stock quantity is adequate
        if order_data["quantity"] > product_response.json()["data"]["quantity"]:
            return JsonResponse(status=400, data={"error": {"code": 400, "message": "No sufficient stock"}})
    if product_response.status_code == 404:
        return JsonResponse(status = 404, data = {"error": {"code": 404, "message": "Product not found"}})
    
    USE_RAFT = True if os.environ.get("USE_RAFT") == "True" else False
    if not USE_RAFT:
        # Send the order request to the catalog server
        order_response = requests.post(f"http://{CATALOG_SERVER_HOST}:{CATALOG_SERVER_PORT}/orders/", json=order_data)
        if order_response.status_code == 200:
            # Create the order log
            with orders_lock:
                order = Order.objects.create(
                    product_name=order_data["name"],
                    quantity=order_data["quantity"]
                )

            # Send order data to other replicas for synchronizing order log
            for id, port in ORDER_SERVER_PORTS.items():
                if id is not order_leader_ID:
                    try:
                        replica_order_response = requests.post(f"http://{ORDER_SERVER_HOST}:{port}/replicas/orders/", json=order_data)
                    except Exception as e:
                        pass
            return JsonResponse(status=200, data={"data": model_to_dict(order, exclude=['product_name', 'quantity'])})
        else:
            return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    else:
        '''
        If raft is enabled, do the following steps:
        1. Check if the current server is the leader, only leader can accept the request.
        2. Use order_data to create order object, but don't save it to the database at this point.
        3. Append order object, term and command to the log.
        4. Send append_entries RPC to all other servers.
        5. Check success replies is majority or not.
        6. If majority, save order, log object to the database (committed), and send success response to the client.
        7. If not majority, send error response to the client.
        8. Update commitIndex and lastApplied, and send append_entries RPC to all other servers.
        '''
        
        from order.wsgi import raft_instance
        if raft_instance.currentState != RaftConfig.LEADER:
            return JsonResponse(status=503, data={"error": {"code": 503, "message": "Not Leader can't accept request"}})
        
        term = raft_instance.currentTerm
        ok, order = raft_instance.append_entry(term, f'''Buy {order_data["quantity"]} {order_data["name"]}''', order_data)
        print('ok', ok, order, model_to_dict(order))
        if ok:
            return JsonResponse(status=200, data={"data": model_to_dict(order, exclude=['product_name', 'quantity'])})
        else:
            return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})

def process_post_replicas_leader_request(leader_data):
    global order_leader_ID, order_leader_port
    try:
        # Set the ID and the port of the leader order server
        order_leader_ID = leader_data["leader_id"]
        order_leader_port = ORDER_SERVER_PORTS[order_leader_ID]
        return HttpResponse(status=204)
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    

def process_post_replicas_order_request(order_data):
    try:
        # Create the order log
        with orders_lock:
            order = Order.objects.create(
                product_name=order_data["name"],
                quantity=order_data["quantity"]
            )
        return HttpResponse(status=204)
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    
def process_get_sync_orders_request(next_order_number):
    try:
        # Query for all orders from next_id to the latest
        with orders_lock:
            orders = Order.objects.filter(order_number__gte=next_order_number).values()

        return JsonResponse(status=200, data={"data": {"orders": list(orders)}})
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_GET
def get_order(request, order_number):
    print(order_leader_ID, order_leader_port)
    try:
        # Submit a task to the thread pool executor
        future = executor.submit(process_get_order_request, order_number)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_POST
def post_order(request):
    try:
        # Extract data from the request
        order_data = json.loads(request.body)
        print(order_data)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_order_request, order_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


@require_POST
def post_replicas_leader(request):
    try:
        # Extract data from the request
        leader_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_replicas_leader_request, leader_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})
    

@require_POST
def post_replicas_order(request):
    try:
        # Extract data from the request
        order_data = json.loads(request.body)
        # Submit a task to the thread pool executor
        future = executor.submit(process_post_replicas_order_request, order_data)
        # Wait for the result of execution
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})

@require_GET
def get_sync_orders(request, next_order_number):
    print(order_leader_ID)
    try:
        future = executor.submit(process_get_sync_orders_request, next_order_number)
        response = future.result()
        return response
    except Exception as e:
        return JsonResponse(status=500, data={"error": {"code": 500, "message": "Internal server error"}})


# Raft endpoints
@require_POST
def handle_vote(request):
    from order.wsgi import raft_instance
    try:
        data = json.loads(request.body)
        term = data['Term']
        candidate_id = data['CandidateId']
        last_log_index = data['LastLogIndex']
        last_log_term = data['LastLogTerm']

        with raft_instance.mu:
            print(f"Receive vote request, my server term {raft_instance.currentTerm}, candidate_id {candidate_id} args term {term}")
    
            # If the candidate's term is less than the current term, reject the vote
            if term < raft_instance.currentTerm:
                return JsonResponse({'VoteGranted': False, 'Term': raft_instance.currentTerm})
            # If the candidate's term is greater than the current term, update the current term and vote for the candidate
            if term > raft_instance.currentTerm:
                raft_instance.currentTerm = term
                raft_instance.votedFor = None
                raft_instance.currentState = RaftConfig.FOLLOWER
                raft_instance.server_state.update_term(term, None)

            print(f'''last_log_index: {last_log_index}, len(raft_instance.logs) - 1): {len(raft_instance.logs) - 1}''')
            print(f'''last_log_term: {last_log_term}, raft_instance.logs {raft_instance.logs}''')

            is_logs =  (last_log_index >= len(raft_instance.logs) - 1) and \
                            (last_log_term >= raft_instance.logs[-1]['term'] if raft_instance.logs else True)
            print(f'''is_logs: {is_logs}''')
            
            # If the term is the same and the candidate's log is at least as up-to-date as the receiver's log, grant the vote
            if (raft_instance.votedFor is None or raft_instance.votedFor == candidate_id) and is_logs:
                raft_instance.votedFor = candidate_id
                raft_instance.currentTerm = term
                raft_instance.server_state.update_term(term, candidate_id)
                raft_instance.currentState = RaftConfig.FOLLOWER
                raft_instance.lastHeartbeatTime = time.time()
                print(f'''raft_instance.votedFor: {raft_instance.votedFor}, candidate_id: {candidate_id}, raft_instance.me: {raft_instance.me}''')
                return JsonResponse({'VoteGranted': True, 'Term': raft_instance.currentTerm})
            else:
                return JsonResponse({'VoteGranted': False, 'Term': raft_instance.currentTerm})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
def handle_append_entries(request):
    from order.wsgi import raft_instance
    try:
        data = json.loads(request.body)
        term = data['Term']
        leader_id = data['LeaderId']
        prev_log_index = data['PrevLogIndex']
        prev_log_term = data['PrevLogTerm']
        entries = data.get('Entries', [])
        leader_commit = data['LeaderCommit']

        with raft_instance.mu:
            if term < raft_instance.currentTerm:
                return JsonResponse({'success': False, 'term': raft_instance.currentTerm})
            print("data", data)
            print("raft_instance.logs", raft_instance.logs)
            print("raft_instance.commitIndex", raft_instance.commitIndex)
            if term > raft_instance.currentTerm:
                raft_instance.currentTerm = term
                raft_instance.votedFor = None # new term so no vote yet
                raft_instance.currentState = RaftConfig.FOLLOWER
                raft_instance.server_state.update_term(term, None)
                print(f"Updated term to {term} and switched to follower due to higher term received.")

            raft_instance.lastHeartbeatTime = time.time()
            raft_instance.leaderId = leader_id

            # Check if the previous log matches
            if prev_log_index >= 1 and len(raft_instance.logs) >= prev_log_index:
                log_term = raft_instance.logs[prev_log_index - 1]['term']
                if log_term != prev_log_term:
                    return JsonResponse({'success': False, 'term': raft_instance.currentTerm})
                
            print("prev_log_index", prev_log_index)
            # Append entries to the log
            if entries:
                raft_instance.logs = raft_instance.logs[:prev_log_index]
                raft_instance.logs.extend(entries)

            print("raft_instance.logs", raft_instance.logs)
            # Update commitIndex and apply to state machine
            if leader_commit > raft_instance.commitIndex:
                raft_instance.commitIndex = min(leader_commit, len(raft_instance.logs))
                with transaction.atomic():
                    print(raft_instance.lastApplied + 1, raft_instance.commitIndex + 1)
                    for i in range(raft_instance.lastApplied + 1, raft_instance.commitIndex + 1):
                        log_entry = raft_instance.logs[i - 1]
                        print(log_entry)
                        order_data = log_entry['order']
                        order = Order(
                            product_name=order_data['product_name'],
                            quantity=order_data['quantity']
                        )
                        order.save()
                        log_entry = LogEntry(
                            index=log_entry['index'],
                            term=log_entry['term'],
                            command=log_entry['command'],
                            order=order
                        )
                        log_entry.save()
                        print(f"Applied log to state machine: {order}")

                raft_instance.lastApplied = raft_instance.commitIndex
                print(f"Updated lastApplied to {raft_instance.lastApplied}")


            # If entries is empty, it is a heartbeat message
            if not entries: 
                print(f'''Received heartbeat message from leader {leader_id}''')
                return JsonResponse({'success': True, 'term': term})
            
            # Update commitIndex
            if leader_commit > raft_instance.commitIndex:
                raft_instance.commitIndex = min(leader_commit, len(raft_instance.logs))
        return JsonResponse({'success': True, 'term': raft_instance.currentTerm})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)


        