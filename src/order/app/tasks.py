from celery import shared_task
from .utils import leader
import os

@shared_task
def init_order_data():

    '''
        Before starting the order server, do the following steps:
        1. Get the leader from frontend first, if there is no leader, the current server will be the leader.
        2. If leader exists, try to synchronize with the leader to retrieve the order information that current server may miss during the offline time.
        3. If current order server ID is higher than the leader, tell frontend to switch leader by simply doing the leader election.
    '''


    leader_ID, leader_port = leader.get_current_leader()
    print(f"Current leader ID is {leader_ID}")

    current_ID = os.getenv('ORDER_SERVER_ID')
    if not current_ID:
        return
    
    if not leader_ID:
        leader.set_self_as_leader(current_ID)
    else:
        print("Start synchronize orders")
        leader.synchronize_orders(leader_port)
        if int(current_ID) > int(leader_ID):
            leader.set_self_as_leader(current_ID)

    return 