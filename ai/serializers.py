from rest_framework import serializers

from .models import AIQueryHistory


class AskAIRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=1)


class RAGQueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1)


class IngestDocRequestSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(min_value=1)


class AIQueryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQueryHistory
        fields = ["id", "query_type", "prompt", "response", "created_at"]
        read_only_fields = ["id", "query_type", "prompt", "response", "created_at"]
