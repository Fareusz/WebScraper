from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    plain_body = models.TextField()
    published_at = models.DateTimeField(null=False, blank=False) # dd.mm.yyyy HH:mm:ss
    url = models.URLField(max_length=500, unique=True)
