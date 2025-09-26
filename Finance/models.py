from django.db import models

class Income(models.Model):
    date = models.DateField(auto_now_add=True)
    perticulers = models.CharField(max_length=255)
    amount = models.FloatField()
    bill_number = models.CharField(max_length=20, default="No Bill")
    other = models.CharField(max_length=255, default=" ", null=True, blank=True)


class Expence(models.Model):
    date = models.DateField(auto_now_add=True)
    perticulers = models.CharField(max_length=255)
    amount = models.FloatField()
    bill_number = models.CharField(max_length=20, default="No Bill")
    other = models.CharField(max_length=255, default=" ",null=True, blank=True)
