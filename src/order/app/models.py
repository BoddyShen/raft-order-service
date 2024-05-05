from django.db import models
from django.forms.models import model_to_dict

class Order(models.Model):
    order_number = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order Number: {self.order_number}, Product: {self.product_name}, Quantity: {self.quantity}"

    def to_dict(self):
        return {
            'order_number': self.order_number,
            'product_name': self.product_name,
            'quantity': self.quantity,
        }
# Raft 
class LogEntry(models.Model):
    index = models.IntegerField(null=True)
    term = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='log_entries')
    command = models.TextField(max_length=255,null=True, default='default_command')

    class Meta:
        db_table = 'log_entries'
    
    def to_dict(self):
        return {
            'index': self.index,
            'term': self.term,
            'order': model_to_dict(self.order, fields=['product_name', 'quantity']),
            'command': self.command,
        }

class RaftServer(models.Model):
    current_term = models.IntegerField(default=0)
    voted_for = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'raft_server'
    
    def update_term(self, new_term, candidate_id=None):
        """Update the current term and the candidate voted for."""
        self.current_term = new_term
        self.voted_for = candidate_id
        self.save()