from django.apps import AppConfig
from django.conf import settings
from . import views

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        if not getattr(settings, 'TESTING', False):
            views.find_order_leader()
    