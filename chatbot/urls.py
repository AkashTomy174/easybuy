from django.urls import path

from . import views


urlpatterns = [
    path("start/", views.start_session, name="chatbot_start"),
    path("message/", views.send_message, name="chatbot_message"),
    path("history/", views.history, name="chatbot_history"),
    path("quick-replies/", views.quick_replies, name="chatbot_quick_replies"),
]

