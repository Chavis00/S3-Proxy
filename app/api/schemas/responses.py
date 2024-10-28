from pydantic import BaseModel


class FileUploadedResponse(BaseModel):
    message: str = "File uploaded successfully"
    status_code: int = 200
