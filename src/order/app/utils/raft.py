import threading
import time
import os
import random
import requests
from datetime import timedelta
from django.db import transaction
from app.models import Order, LogEntry, RaftServer
from app.utils.constants import ORDER_SERVER_HOST, ORDER_SERVER_PORTS

USE_DELAY = True if os.environ.get("USE_DELAY") == "True" else False


class RaftConfig:
    HEARTBEAT_TIMEOUT = timedelta(milliseconds=1500)
    ELECT_TIMEOUT_BASE = timedelta(milliseconds=5000)
    ELECT_TIMEOUT_CHECK_INTERVAL = timedelta(milliseconds=3000)
    FOLLOWER   	= 0
    CANDIDATE 	= 1
    LEADER     	= 2

class RequestVoteArgs:
    def __init__(self, term, candidate_id, last_log_index, last_log_term):
        self.Term = term # candidate’s term
        self.CandidateId = candidate_id # candidate requesting vote
        self.LastLogIndex = last_log_index # index of candidate’s last log entry
        self.LastLogTerm = last_log_term # term of candidate’s last log entry

class RequestVoteReply:
    def __init__(self):
        self.Term = 0 # currentTerm, for candidate to update itself
        self.VoteGranted = False # true means candidate received vote

class AppendEntriesArgs:
    def __init__(self, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
        self.term = term # leader’s term
        self.leader_id = leader_id # so follower can redirect clients
        self.prev_log_index = prev_log_index # index of log entry immediately preceding new ones
        self.prev_log_term = prev_log_term # term of prevLogIndex entry
        self.entries = entries  # log entries to store (empty for heartbeat; may send more than one for efficiency)
        self.leader_commit = leader_commit # leader’s commitIndex

class AppendEntriesReply:
    def __init__(self):
        self.term = 0 # currentTerm, for leader to update itself
        self.success = False # true if follower contained entry matching prevLogIndex and prevLogTerm  

class Raft:
    def __init__(self, server_id, peers):
        self.mu = threading.Lock()
        self.peers = peers  
        self.me = server_id
        self.dead = False
        
        # Initial persistent state from database
        self.server_state, created = RaftServer.objects.get_or_create(pk=1)
        self.logs = [log_entry.to_dict() for log_entry in LogEntry.objects.all().order_by('id')]
        self.currentTerm = self.server_state.current_term # latest term server has seen (initialized to 0 on first boot, increases monotonically)
        self.votedFor = self.server_state.voted_for # candidateId that received vote in current term (or null if none)

        # Initial volatile state
        self.commitIndex = self.logs[-1]['index'] if self.logs else 0 # index of highest log entry known to be committed (initialized to 0, increases monotonically)
        self.lastApplied = self.logs[-1]['index'] if self.logs else 0 # index of highest log entry applied to state machine (initialized to 0, increases monotonically)

        # Leader state
        self.nextIndex = {id: len(self.logs) + 1 for id, url in peers} # for each server, index of the next log entry to send to that server (initialized to leader last log index + 1)
        self.matchIndex = {id: 0 for id, url in peers} # for each server, index of highest log entry known to be replicated on server (initialized to 0, increases monotonically)

        self.leaderId = None
        self.currentState = RaftConfig.FOLLOWER 
        self.lastHeartbeatTime = time.time()
    
    # return currentTerm and whether this server believes it is the leader.
    def get_state(self):
        with self.mu:
            term = self.currentTerm
            is_leader = (self.currentState == RaftConfig.LEADER)
            return term, is_leader

    def get_leader_url(self):
        return f'''http://{ORDER_SERVER_HOST}:{ORDER_SERVER_PORTS[str(self.leaderId)]}''' if self.leaderId else None

    
    def ticker(self):
        '''
        This function is called periodically to check if the server has timed out and needs to start a new election.
        '''
        while not self.dead and self.currentState != RaftConfig.LEADER:
            time.sleep(RaftConfig.ELECT_TIMEOUT_CHECK_INTERVAL.total_seconds())
            with self.mu:
                elapsed_time = time.time() - self.lastHeartbeatTime
                random_timeout = RaftConfig.ELECT_TIMEOUT_BASE.total_seconds() + random.randint(0, 250) / 1000.0
            if elapsed_time >= random_timeout:
                print(f"Server {self.me} election timeout, start new election")
                self.start_election()
    
    def send_request_vote(self, server_url, args, reply):
        url = f"{server_url}/vote/"
        data = {
            'Term': args.Term,
            'CandidateId': args.CandidateId,
            'LastLogIndex': args.LastLogIndex,
            'LastLogTerm': args.LastLogTerm
        }
        
        try:
            response = requests.post(url, json=data)
            response_data = response.json()
            
            reply.VoteGranted = response_data.get('VoteGranted', False)
            reply.Term = response_data.get('Term', args.Term)
            print(f'''VoteGranted: {reply.VoteGranted}, Term: {reply.Term}''')
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False

    def start_election(self):
        '''
        Start a new election by incrementing the current term and requesting votes from other servers.
        '''
        with self.mu:
            self.currentTerm += 1
            self.votedFor = self.me
            self.server_state.update_term(self.currentTerm, self.me)
            self.currentState = RaftConfig.CANDIDATE
            self.lastHeartbeatTime = time.time()
            votesReceived = 1
        print(f"Server {self.me} starting an election in term {self.currentTerm}.")

        def request_vote(server_url):
            args = RequestVoteArgs(self.currentTerm, self.me, len(self.logs) - 1,
                                    self.logs[-1]['term'] if self.logs else 0)
            reply = RequestVoteReply()
            ok = self.send_request_vote(server_url, args, reply)
            print(f'''ok: {ok}, reply.VoteGranted: {reply.VoteGranted}''')
            if ok and reply.VoteGranted:
                nonlocal votesReceived
                with self.mu:
                    votesReceived += 1
                print(f'''votesReceived {votesReceived}, majority requirement {len(self.peers) / 2}''')
                if votesReceived > len(self.peers) / 2 and self.currentState != RaftConfig.LEADER:
                    with self.mu:
                        self.currentState = RaftConfig.LEADER
                        self.leaderId = self.me
                    self.send_heart_beats()
                    
        threads = []
        # Send request vote to all peers
        for i, url in self.peers:
            if i != self.me:
                print(f'''Sending request vote to server {i} at {url}''')
                thread = threading.Thread(target=request_vote, args=(url,))
                threads.append(thread)
                thread.start()
        
        # Wait for all threads to finish
        for thread in threads:
            thread.join()
    
    def send_heart_beats(self):
        '''Send heartbeats to all peers to maintain leadership status.'''
        print(f"Server {self.me} is now the leader, sending heartbeats.")

        def heartbeat_loop():
            while self.currentState == RaftConfig.LEADER:
                args = AppendEntriesArgs(
                    term=self.currentTerm,
                    leader_id=self.me,
                    prev_log_index=len(self.logs) - 1,
                    prev_log_term=self.logs[-1]['term'] if self.logs else 0,
                    entries=[],
                    leader_commit=self.commitIndex
                )
                replies = []
                threads = []
                for i, peer in self.peers:
                    if i != self.me:
                        reply = AppendEntriesReply()
                        thread = threading.Thread(target=self.send_append_entries, args=(peer, args, reply))
                        threads.append(thread)
                        replies.append(reply)
                        thread.start()
                for thread in threads:
                    thread.join()
                
                # Check replies for higher term to step down as leader
                for reply in replies:
                    if reply.term > self.currentTerm:
                        print(f'''reply.term: {reply.term}, self.currentTerm: {self.currentTerm}''')
                        with self.mu:
                            self.currentTerm = reply.term
                            self.votedFor = None
                            self.currentState = RaftConfig.FOLLOWER
                            self.server_state.update_term(self.currentTerm, None)
                            print(f"Server {self.me} find higher term. Change to follower")
                            return

                time.sleep(RaftConfig.HEARTBEAT_TIMEOUT.total_seconds())

        # Start the heartbeat loop in a new thread
        threading.Thread(target=heartbeat_loop).start()
            
    def send_append_entries(self, peer, args, reply):
        url = f"{peer}/append_entries/"
        data = {
            'Term': args.term,
            'LeaderId': args.leader_id,
            'PrevLogIndex': args.prev_log_index,
            'PrevLogTerm': args.prev_log_term,
            'Entries': args.entries,
            'LeaderCommit': args.leader_commit
        }
        try:
            response = requests.post(url, json=data)
            response_data = response.json()
            
            reply.success = response_data.get('success', False)
            reply.term = response_data.get('term', args.term)
            return response.status_code == 200
        
        except requests.RequestException as e:
            # print(f"Network error when sending heartbeat to {peer}: {e}")
            pass
    
    def append_entry(self, term, command, order_data):
        print("leader logs", self.logs)
        print("commitIndex", self.commitIndex)
        print("lastApplied", self.lastApplied)
        print("nextIndex", self.nextIndex)
        print("matchIndex", self.matchIndex)

        index = len(self.logs) + 1
        entry = {
            'index': index,
            'term': term,
            'command': command,
            'order': {
                'product_name': order_data['name'],
                'quantity': order_data['quantity']
            }
        }
        self.logs.append(entry) # append entry to local log
        if USE_DELAY:
            time.sleep(5)

        replies = []
        threads = []
        for i, peer in self.peers:
            if i != self.me:
                # Send append entry to all peers
                args = AppendEntriesArgs(
                    term=self.currentTerm,
                    leader_id=self.me,
                    prev_log_index=self.nextIndex[i] - 1,
                    prev_log_term=self.logs[self.nextIndex[i] - 1]['term'],
                    entries=self.logs[self.nextIndex[i]-1:], # Send log entries starting from nextIndex
                    leader_commit=self.commitIndex
                )
                num_entries_to_send = len(args.entries)
                reply = AppendEntriesReply()
                thread = threading.Thread(target=self.send_append_entries, args=(peer, args, reply))
                threads.append(thread)
                replies.append((i, reply, num_entries_to_send))
                thread.start()

        for thread in threads:
            thread.join() # Wait for all threads to finish
        
        try:
            # Check if majority of peers accept the entry and if higher term to step down as leader
            success_count = 1
            for id, reply, num_entries_to_send in replies:
                if reply.term > self.currentTerm:
                    print(f'''reply.term: {reply.term}, self.currentTerm: {self.currentTerm}''')
                    with self.mu:
                        self.currentTerm = reply.term
                        self.votedFor = None
                        self.currentState = RaftConfig.FOLLOWER
                        self.server_state.update_term(self.currentTerm, None)

                        print(f"Server {self.me} find higher term. Change to follower")
                        self.logs.pop() # Remove the entry from the log
                        return False, None
                print(id, reply.success)
                if reply.success:
                    with self.mu:
                        self.nextIndex[id] = self.nextIndex[id] + num_entries_to_send
                        self.matchIndex[id] = self.nextIndex[id] - 1
                    success_count += 1
                else:
                    # Decrement nextIndex on failure to find the match
                    with self.mu:
                        self.nextIndex[id] = max(self.nextIndex[id] - 1, 1)

            if success_count > len(self.peers) / 2:
                with self.mu:
                    self.commitIndex = entry['index']
                    self.lastApplied = entry['index']

                with transaction.atomic():
                    order = Order.objects.create(
                        product_name=order_data['name'],
                        quantity=order_data['quantity']
                    )
                    log_entry = LogEntry(
                        index=entry['index'],
                        term=entry['term'],
                        command=entry['command'],
                        order=order
                    )
                    log_entry.save()
                print(f'''Server {self.me} append {entry} success''')
                print(order)
                return True, order
            self.logs.pop()
            return False, None
        except Exception as e:
            print(e)
            print(f"Error when appending entry: {e}")
            self.logs.pop()
            return False, None