from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('products/<str:product_name>/', views.get_product),
    path('orders/', csrf_exempt(views.post_order)),
]