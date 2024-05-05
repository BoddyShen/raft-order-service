from django.apps import AppConfig
from django.conf import settings
import os
from . import views

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        USE_RAFT = True if os.environ.get("USE_RAFT") == "True" else False
        if not getattr(settings, 'TESTING', False) and not USE_RAFT:
            views.find_order_leader()
    