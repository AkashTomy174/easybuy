@echo off
echo Starting Django Celery test - Ensure Redis running!
cd easybuy
start cmd /k "python manage.py runserver 0.0.0.0:8000"
timeout /t 3
start cmd /k "celery -A easybuy.easybuy worker -l info"
echo Servers started. Test with: python ..\test_celery.py
pause
