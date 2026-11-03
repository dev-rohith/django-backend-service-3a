from django.urls import re_path

from documents.views import (
    DocumentDetailView,
    DocumentListCreateView,
    QueryLogListView,
    RunQueryView,
)

urlpatterns = [
    re_path(r"^documents/?$", DocumentListCreateView.as_view(), name="document-list-create"),
    re_path(r"^documents/(?P<pk>\d+)/?$", DocumentDetailView.as_view(), name="document-detail"),
    re_path(r"^query/?$", RunQueryView.as_view(), name="run-query"),
    re_path(r"^queries/?$", QueryLogListView.as_view(), name="query-log-list"),
]
