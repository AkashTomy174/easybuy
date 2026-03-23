#!/usr/bin/env python
\"\"\"Fixed Celery test - no Redis needed.\"\"\"
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

try:
    from easybuy.core.tasks import send_notification_task
    print('Task imported successfully')
except Exception as e:
    print(f'Import error: {e}')
    exit(1)

print('Dispatching test task...')
result = send_notification_task.delay(1)
print(f'Task ID: {result.id}')
print(f'Initial Status: {result.status}')

import time
time.sleep(10)
print(f'Final Status: {result.status}')
if result.ready():
    print(f'Result: {result.result}')
else:
    print('PENDING - start worker with: celery -A easybuy.easybuy worker -l info')
