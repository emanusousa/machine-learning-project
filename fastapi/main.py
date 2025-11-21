from fastapi import FastAPI, HTTPException, UploadFile, status
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from uuid import uuid4
from loguru import logger
import magic
import boto3
import os

load_dotenv()

SUPPORTED_FILE_TYPES = {
    'text/csv': 'csv',
    'application/json': 'json'
}

AWS_BUCKET = os.environ.get("AWS_BUCKET")
AWS_REGION = os.environ.get("AWS_REGION")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

s3 = boto3.resource(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

bucket = s3.Bucket(AWS_BUCKET)

async def s3_upload(contents: bytes, key: str):
    logger.info(f'Uploading {key} to S3...')
    bucket.put_object(Key=key, Body=contents)
    logger.info(f'{key} uploaded successfully.')

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <body>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input name="file" type="file">
                <button type="submit">Enviar</button>
            </form>
        </body>
    </html>
    """

@app.post('/upload')
async def upload(file: UploadFile | None = None):
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum arquivo encontrado."
        )

    contents = await file.read()
    file_type = magic.from_buffer(buffer=contents, mime=True)

    if file_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado {file_type} - o tipo precisa ser {SUPPORTED_FILE_TYPES}"
        )

    file_key = f'{uuid4()}.{SUPPORTED_FILE_TYPES[file_type]}'
    await s3_upload(contents=contents, key=file_key)

    return {"message": "Arquivo enviado com sucesso!", "file_key": file_key}
