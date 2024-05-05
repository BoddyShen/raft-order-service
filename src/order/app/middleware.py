from django.http import JsonResponse
from django.urls import resolve
import os
import requests


class RaftMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code executed before the request is processed
        response = self.process_request(request)
        if response:
            return response
        # Return the response from the view
        return self.get_response(request)

    def process_request(self, request):
        from order.wsgi import raft_instance
        USE_RAFT = True if os.environ.get("USE_RAFT") == "True" else False
        if not USE_RAFT:
            return None
        term, is_leader = raft_instance.get_state()
        if is_leader or (resolve(request.path_info) and resolve(request.path_info).url_name in ['vote', 'append_entries']):
            print("Request pass middleware")
            return None 
        
        # If the current node is not the leader, it can redirect to the leader node or return an error
        print("This server is not leader. Redirecting to leader server.")
        if not is_leader:
            leader_url = raft_instance.get_leader_url()
            if leader_url:
                # Redirect client requests to leader
                print(f"Raft Server {raft_instance.me} redirect {request} to Leader Server at {leader_url}")
                return self.forward_request(request, leader_url)
            else:
                return JsonResponse({"term": term, "error": "Leader not found"}, status=503)
        return None

    def forward_request(self, request, leader_url):
        # Determine the method of the original request
        if request.method == 'POST':
            print(leader_url + request.path, request.body)
            resp = requests.post(leader_url + request.path, data=request.body)
        elif request.method == 'GET':
            resp = requests.get(leader_url + request.path, headers=request.headers)
        else:
            # Optionally handle other methods such as PUT, DELETE, etc.
            return JsonResponse({"error": "Method not supported"}, status=405)

        # Return the response from the leader to the client
        return JsonResponse(resp.json(), status=resp.status_code)