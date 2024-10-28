import os
from typing import BinaryIO, AsyncGenerator
import aioboto3
import asyncio
from app.api.exceptions.custom_exception import UnableToUploadFileException, S3BucketNotFoundException, \
    UnableToDownloadFileException, FileNotFoundInBucket
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3FileManager:
    def __init__(self, limit_size_mb: int = 1):
        self.region_name = os.environ.get('S3_REGION', "us-east-2")
        self.limit_size_mb = limit_size_mb
        self.session = aioboto3.Session()
        self.limit_size_mb = int(os.environ.get('UPLOAD_MULTIPART_LIMIT_MB', 10))
        self.chunk_size_mb = int(os.environ.get('UPLOAD_MULTIPART_CHUNK_SIZE', 5))
        self.download_chunk_size_mb = int(os.environ.get('DOWNLOAD_CHUNK_SIZE', 2))

    @staticmethod
    def calculate_file_size(file: BinaryIO) -> int:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        return file_size

    async def standard_upload(self, s3, file: BinaryIO, bucket_name: str, object_name: str) -> None:
        logger.info(f"Uploading file {object_name} to bucket {bucket_name} using standard upload")
        await s3.upload_fileobj(file, bucket_name, object_name)

    async def multipart_upload(self, s3, file: BinaryIO, bucket_name: str, object_name: str) -> None:
        logger.info(f"Uploading file {object_name} to bucket {bucket_name} using multipart upload")
        response = await s3.create_multipart_upload(Bucket=bucket_name, Key=object_name)
        upload_id = response['UploadId']
        parts = []
        part_number = 1
        while True:
            data = await asyncio.to_thread(file.read, self.chunk_size_mb * 1024 * 1024)
            if not data:
                break
            part_response = await s3.upload_part(
                Bucket=bucket_name,
                Key=object_name,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=data
            )
            parts.append({'PartNumber': part_number, 'ETag': part_response['ETag']})
            part_number += 1
            logger.info(f"Uploaded part {part_number} of {object_name}")
        await s3.complete_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id,
                                           MultipartUpload={'Parts': parts})

    async def upload_file_into_s3(self, file: BinaryIO, bucket_name: str, object_name: str) -> None:
        async with self.session.client('s3', region_name="us-east-2") as s3:
            try:
                if self.calculate_file_size(file) < self.limit_size_mb * 1024 * 1024:
                    await self.standard_upload(s3, file, bucket_name, object_name)
                else:
                    await self.multipart_upload(s3, file, bucket_name, object_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchBucket':
                    logger.error(f"Bucket {bucket_name} does not exist.")
                    raise S3BucketNotFoundException(bucket_name)
                else:
                    logger.error(f"Error uploading file: {e}")
                    raise UnableToUploadFileException(e)
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                raise UnableToUploadFileException(e)

    async def download_file_from_s3(self, bucket_name: str, object_name: str) -> AsyncGenerator[
        bytes, None]:
        logger.info(f"Downloading file {object_name} from bucket {bucket_name} using streaming download")
        async with self.session.client('s3', region_name="us-east-2") as s3:
            head_object = await s3.head_object(Bucket=bucket_name, Key=object_name)
            content_length = head_object["ContentLength"]
            for offset in range(0, content_length, self.download_chunk_size_mb * 1024 * 1024):
                end = min(offset + (self.download_chunk_size_mb * 1024 * 1024) - 1, content_length - 1)
                s3_file = await s3.get_object(Bucket=bucket_name, Key=object_name, Range=f"bytes={offset}-{end}")

                async with s3_file["Body"] as stream:
                    yield await stream.read()

    async def check_file_exists_and_get_metadata(self, bucket_name: str, object_name: str) -> dict:
        async with self.session.client('s3', region_name="us-east-2") as s3:
            try:
                head_object = await s3.head_object(Bucket=bucket_name, Key=object_name)
                return head_object
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    raise FileNotFoundInBucket(object_name, bucket_name)
                else:
                    raise UnableToDownloadFileException(e)
