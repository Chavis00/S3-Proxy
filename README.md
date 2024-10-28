# S3 Proxy

## Description
This is a basic proxy service for AWS S3, built with FastAPI. The service allows you to upload and download files to a specific S3 bucket.

## Possible problems approached in this project:
- Managing multiple request at the same time
- Upload files larger than memory when its necessary
- Streaming Download
- Custom Http Exception with Responses
## Solutions
- Using gunicorn and asynchronous programming to manage multiple request at the same time without blocking main thread (only usable thread because python's GIL)
- Using both standard upload and multipart upload to S3, configurable by the env variable `UPLOAD_MULTIPART_LIMIT_MB` if the file exceed the limit will be uploaded by parts (multipart upload) 
- Configurable size of the chunks in case of using multipart upload configurable by the env variable `UPLOAD_MULTIPART_CHUNK_SIZE` (aws S3 can manage a min of 5mb chunk)
- Streaming Downloading by chunks to no charging the file in memory configurable by env variable  `DOWNLOAD_CHUNK_SIZE`
## TODOs
- More tests
- Authentication, Authorization
- CICD pipelines
- Kubernetes config if its needed 
- If I know the application always will manage large files I would use Celery and RabbiMQ for uploading files, and return some status of the file saved in a db, so the client could GET file uploading status when is required  

## Endpoints
### - [POST] /files

Example of use
```bash
curl --location 'http://127.0.0.1:8000/files/' \                                                                                               
--form 'bucket_name="your_bucket_name"' \
--form 'object_name="your_object_name"' \
--form 'file_request=@"/path/to/file"'
```
#### Possible Responses
- When File Upload Succesfully HTTP 200: 
```json
{
  "detail":"File uploaded successfully",
  "status_code":200
}
```
- When Bucket not found HTTP 404: 
```json
{
  "detail":"Bucket bucket_name does not exist."
}
```
- When File is unreadable HTTP 400: 
```json
{
  "detail": "File is empty or not readable."
}
```
- When sent a bad request to S3 HTTP 400: 
```json
{
  "detail": "Unable to upload file to S3 {ERROR}" 
}
```


### - [GET] /files
```bash
curl --location 'http://127.0.0.1:8000/files?bucket_name=your_bucket_name&object_name=your_object_name' \
```
#### Possible Responses
 - If File is located will start a Streaming download with HTTP 200
 - If File not found HTTP 400

```json
{
  "detail": "File {object_name} or bucket {bucket_name} not found." 
}
```
## How to Run
### Environment Variables
Set environment variables or create a .env file (if you run docker-compose) in the root directory of the project with the following variables:
```file
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
UPLOAD_MULTIPART_LIMIT_MB=
UPLOAD_MULTIPART_CHUNK_SIZE= # at least 5mb min
DOWNLOAD_CHUNK_SIZE=
S3_REGION=
```
### Test
To run the tests locally you should run the following command in the root directory of the project
```bash
pytest /tests
```
### Docker run

```bash
docker build -t s3_proxy .
docker run -d \
  --name s3-proxy \
  -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=tu_access_key \
  -e AWS_SECRET_ACCESS_KEY=tu_secret_key \
  -e UPLOAD_MULTIPART_LIMIT_MB=10 \
  -e UPLOAD_MULTIPART_CHUNK_SIZE=5 \
  -e DOWNLOAD_CHUNK_SIZE=10 \
  -e S3_REGION=us-east-2 \
  s3_proxy:latest
```
### Docker Compose
```bash
docker-compose up --build
```