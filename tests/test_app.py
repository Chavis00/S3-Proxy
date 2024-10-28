from http import HTTPStatus
from io import BytesIO

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError
from app.app import app
from app.api.exceptions.custom_exception import S3BucketNotFoundException, FileNotFoundInBucket
from app.pkg.s3_helper import S3FileManager

s3_manager = S3FileManager()
@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_upload_file_success(mocker, client):
    mock_s3 = AsyncMock()
    mocker.patch("aioboto3.Session.client", return_value=mock_s3)

    mock_s3.create_bucket.return_value = None

    file_content = b"dummy file content"
    file = BytesIO(file_content)
    file.name = "testfile.txt"

    response = client.post(
        "/files",
        files={
            "file_request": (file.name, file, "text/plain"),
        },
        data={
            "bucket_name": "test-bucket",
            "object_name": "testfile.txt"
        }
    )

    assert response.status_code == HTTPStatus.OK

@pytest.mark.asyncio
async def test_upload_file_fail_empty_file(mocker, client):
    mock_s3 = AsyncMock()
    mocker.patch("aioboto3.Session.client", return_value=mock_s3)

    mock_s3.create_bucket.return_value = None

    file = BytesIO()
    file.name = "testfile.txt"
    response = client.post(
        "/files",
        files={
            "file_request": (file.name, None, "text/plain"),
        },
        data={
            "bucket_name": "test-bucket",
            "object_name": "testfile.txt"
        }
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_bucket_not_found(mocker):
    mock_s3 = AsyncMock()

    mocker.patch("aioboto3.Session.client", return_value=mock_s3)

    mocker.patch("app.pkg.s3_helper.S3FileManager.standard_upload", side_effect=ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
        "PutObject"
    ))

    file_content = b"dummy file content"
    file = BytesIO(file_content)
    file.name = "testfile.txt"

    with pytest.raises(S3BucketNotFoundException) as excinfo:
        await s3_manager.upload_file_into_s3(file, "test-bucket", "testfile.txt")

    assert "Bucket test-bucket does not exist" in str(excinfo.value)


@pytest.mark.asyncio
async def test_download_file_success(mocker, client):
    mock_s3 = AsyncMock()

    mocker.patch("aioboto3.Session.client", return_value=mock_s3)

    mocker.patch(
        "app.pkg.s3_helper.S3FileManager.check_file_exists_and_get_metadata",
        return_value={"ContentLength": 1024, "ContentType": "text/plain"}
    )

    async def mock_file_generator():
        yield b"chunk1"
        yield b"chunk2"

    mocker.patch(
        "app.pkg.s3_helper.S3FileManager.download_file_from_s3",
        return_value=mock_file_generator()
    )

    # Llamada asincrónica al endpoint
    response = client.get("/files?bucket_name=test-bucket&object_name=testfile.txt")

    # Asegúrate de que la respuesta sea la esperada
    assert response.status_code == HTTPStatus.OK
    assert response.headers["X-File-Name"] == "testfile.txt"
    assert response.headers["X-File-Type"] == "text/plain"
    assert response.headers["X-File-Size"] == "1024"
    assert response.content == b"chunk1chunk2"
