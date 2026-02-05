from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class PlatformReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username}"
