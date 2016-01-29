from django.db import models


class Counter(models.Model):

    counter = models.PositiveIntegerField()

    def __str__(self):

        return str(self.counter)
