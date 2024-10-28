from pydantic.v1 import BaseModel


class UploadFileRequest(BaseModel):
    bucket_name: str
    object_name: str
