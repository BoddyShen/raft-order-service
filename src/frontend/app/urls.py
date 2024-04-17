from . import views
from django.urls import path
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('products/<str:product_name>/', views.get_product),
    path('orders/<str:order_number>/', views.get_order),
    path('orders/', csrf_exempt(views.post_order)),
    path('cache/<str:product_name>/', csrf_exempt(views.delete_cache)),
]

views.find_order_leader()