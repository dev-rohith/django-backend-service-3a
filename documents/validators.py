from django.core.exceptions import ValidationError

from documents.constants import MAX_UPLOAD_SIZE_MB


def validate_file_size(uploaded_file):
    max_size_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_size_bytes:
        raise ValidationError(f"File is too large. Max size is {MAX_UPLOAD_SIZE_MB}MB.")
