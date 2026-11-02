import asyncio
import uvicorn
from fastapi import FastAPI, UploadFile, File, Request
from pydantic import BaseModel
from aws_s3 import put_file
from aws_bedrock import AWSBedRock
from fastapi.templating import Jinja2Templates

app = FastAPI(title="CookBook Recipie")

class UploadResponse(BaseModel):
    message: dict
    filename: str


class SearchQuery(BaseModel):
    query: str
    top_k: int=3

# Configure templates
templates = Jinja2Templates(directory="templates")

bedrock_obj = AWSBedRock()

@app.post("/upload-file", response_model=UploadResponse)
async def upload_file(file: UploadFile=File(...)):
    content = await file.read()
    filename = file.filename
    res = await asyncio.to_thread(put_file,file_content=content, filename=filename)
    if res == 200:
        bedrock_injestion_res = {}
        # bedrock_injestion_res = await asyncio.to_thread(bedrock_obj.start_ingestion())
    return {"message": bedrock_injestion_res, "filename":filename}


@app.post("/search")
async def get_query(request: SearchQuery):
    res = await asyncio.to_thread(bedrock_obj.retrieve_ingestion, request.query, request.top_k)
    return res


@app.get("/")
async def read_root(request: Request):
    """Serve the main UI page"""
    return templates.TemplateResponse(request,"index.html")


@app.get("/health")
async def health_check(request: Request):
    """Serve the main UI page"""
    return {"health":"Ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
