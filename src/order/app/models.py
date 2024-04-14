from django.db import models


class Order(models.Model):
    order_number = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order Number: {self.order_number}, Product: {self.product_name}, Quantity: {self.quantity}"