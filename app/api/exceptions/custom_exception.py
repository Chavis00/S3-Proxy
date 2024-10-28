from fastapi import HTTPException


class S3BucketNotFoundException(HTTPException):
    def __init__(self, bucket_name: str):
        super().__init__(status_code=404, detail=f"Bucket {bucket_name} does not exist.")


class UnableToUploadFileException(HTTPException):
    def __init__(self, e: Exception):
        super().__init__(status_code=400, detail=f"Unable to upload file to S3: {e}")


class UnableToDownloadFileException(HTTPException):
    def __init__(self, e: Exception):
        super().__init__(status_code=500, detail=f"Unable to download file from S3: {e}")


class FileNotFoundInBucket(HTTPException):
    def __init__(self, object_name: str, bucket_name: str):
        super().__init__(status_code=404, detail=f"File {object_name} or bucket {bucket_name} not found.")
