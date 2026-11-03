from rest_framework import serializers

from agent.models import ChatMessage, ChatSession


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1)
    session_id = serializers.UUIDField(required=False, allow_null=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "sources", "created_at"]
        read_only_fields = fields


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ["session_key", "created_at", "messages"]
        read_only_fields = fields
