from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class SizeLimitUploadHandler(FileUploadHandler):
    """Stop oversized files while Django is receiving the request body."""

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.received_bytes = 0

    def receive_data_chunk(self, raw_data, start):
        self.received_bytes += len(raw_data)
        if self.received_bytes > settings.MAX_UPLOAD_SIZE:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None
