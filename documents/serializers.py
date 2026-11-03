from rest_framework import serializers

from documents.models import Document, QueryLog


class DocumentSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Document
        fields = ["id", "title", "content", "file", "owner", "uploaded_at"]
        read_only_fields = ["owner", "uploaded_at"]
        extra_kwargs = {"file": {"required": False}}

    def validate(self, attrs):
        file = attrs.get("file")
        content = attrs.get("content", "")
        if not file and not content:
            raise serializers.ValidationError(
                "Provide either a file or a content field."
            )
        return attrs


class DocumentListSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Document
        fields = ["id", "title", "content", "owner", "uploaded_at"]
        read_only_fields = ["id", "title", "content", "owner", "uploaded_at"]


class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = ["id", "query_text", "result_summary", "created_at"]
        read_only_fields = ["id", "query_text", "result_summary", "created_at"]


class QueryRequestSerializer(serializers.Serializer):
    query_text = serializers.CharField(max_length=500)
