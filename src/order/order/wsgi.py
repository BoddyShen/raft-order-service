"""
WSGI config for order project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import threading
from django.core.wsgi import get_wsgi_application
from app.utils.raft import Raft, RaftConfig
from app.utils.constants import ORDER_SERVER_HOST, ORDER_SERVER_PORTS

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order.settings')

application = get_wsgi_application()

peers = [(id ,f'''http://{ORDER_SERVER_HOST}:{port}''') for id, port in ORDER_SERVER_PORTS.items()]
global raft_instance
current_ID = os.getenv('ORDER_SERVER_ID')
print(f'''Current ID: {current_ID}''')
raft_instance = Raft(server_id=current_ID, peers=peers) if current_ID else None

if raft_instance:
    ticker_thread = threading.Thread(target=raft_instance.ticker)
    ticker_thread.start()