import logging

from fastapi import UploadFile, Form, APIRouter, Query

from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from app.api.schemas.requests import UploadFileRequest
from app.api.schemas.responses import FileUploadedResponse
from app.pkg.s3_helper import S3FileManager

logger = logging.getLogger(__name__)


class FileRoutes:
    def __init__(self):
        self.router = APIRouter()
        self.s3_manager = S3FileManager()
        self.router.add_api_route("/files", self.upload_file, methods=["POST"])
        self.router.add_api_route("/files", self.download_file, methods=["GET"])

    async def upload_file(
            self,
            file_request: UploadFile,
            bucket_name: str = Form(...),
            object_name: str = Form(...)
    ) -> JSONResponse:
        validated_request = UploadFileRequest(bucket_name=bucket_name, object_name=object_name)
        if file_request.file is None:
            return JSONResponse(content={"detail": "File is empty or not readable."}, status_code=400)
        await self.s3_manager.upload_file_into_s3(file_request.file, validated_request.bucket_name, validated_request.object_name)
        response = FileUploadedResponse()
        return JSONResponse(content=response.model_dump(), status_code=response.status_code)

    async def download_file(
            self,
            bucket_name: str = Query(...),
            object_name: str = Query(...)
    ) -> StreamingResponse:
        file_metadata = await self.s3_manager.check_file_exists_and_get_metadata(bucket_name, object_name)
        file_size = file_metadata["ContentLength"]
        file_type = file_metadata.get("ContentType", "application/octet-stream")
        file_name = object_name
        headers = {
            "X-File-Name": file_name,
            "X-File-Type": file_type,
            "X-File-Size": str(file_size),
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(self.s3_manager.download_file_from_s3(bucket_name, object_name), headers=headers, media_type="application/octet-stream")
