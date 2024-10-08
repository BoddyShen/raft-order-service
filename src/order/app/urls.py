from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('orders/<str:order_number>/', views.get_order),
    path('orders/', csrf_exempt(views.post_order)),
    path('replicas/leaders/', csrf_exempt(views.post_replicas_leader)),
    path('replicas/orders/', csrf_exempt(views.post_replicas_order)),
    path('sync/orders/<str:next_order_number>/', views.get_sync_orders),
    # Raft
    path('vote/', csrf_exempt(views.handle_vote), name='vote'),
    path('append_entries/', csrf_exempt(views.handle_append_entries), name='append_entries'),

]