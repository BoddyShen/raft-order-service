from django.apps import AppConfig
from .tasks import init_order_data

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        init_order_data()