from django.apps import AppConfig
from .utils import leader
import os

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        current_ID = os.getenv('ORDER_SERVER_ID')
        if not current_ID:
            return
        leader.synchronize_orders()