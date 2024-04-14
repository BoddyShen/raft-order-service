from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('orders/<str:order_number>/', views.get_order),
    path('orders/', csrf_exempt(views.post_order)),
]