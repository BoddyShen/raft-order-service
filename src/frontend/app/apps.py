from django.apps import AppConfig
from . import views

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        views.find_order_leader()
    