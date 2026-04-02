import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")

app = Celery("easybuy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()