from django.urls import re_path

from agent.views import ChatHistoryView, ChatView, FileUploadView

urlpatterns = [
    re_path(r"^api/agent/upload/?$", FileUploadView.as_view(), name="agent-upload"),
    re_path(r"^api/agent/chat/?$", ChatView.as_view(), name="agent-chat"),
    re_path(
        r"^api/agent/history/(?P<session_key>[0-9a-f-]{36})/?$",
        ChatHistoryView.as_view(),
        name="agent-history",
    ),
]
