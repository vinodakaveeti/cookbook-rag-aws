# Cookbook RAG

A small recipe search application built with FastAPI, Amazon S3, and Amazon Bedrock Knowledge Bases. Users can upload cookbook documents and ask questions about their contents.

## How it works

- **FastAPI** provides the web page and HTTP API.
- **Amazon S3** stores uploaded cookbook documents.
- **Amazon Bedrock Knowledge Bases** handles document parsing, chunking, embeddings, and retrieval using the Knowledge Base configuration.
- **Amazon Nova Micro** (`amazon.nova-micro-v1:0`) generates an answer from retrieved recipe content.
- **Docker** packages the Python application. A Helm chart is included for Kubernetes deployment; the intended AWS Kubernetes platform is Amazon EKS.

The Knowledge Base's embedding model, vector store, and chunking strategy are configured in AWS. The application does not create or manage those resources itself.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /` | Serves the recipe search web page. |
| `GET /health` | Health check for the application. |
| `POST /upload-file` | Accepts a file upload and stores it in the configured S3 location. |
| `POST /search` | Retrieves relevant cookbook content from the Knowledge Base and asks the model to format an answer. |

### Search request example

```json
{
  "query": "How do I make vegetable biryani?",
  "top_k": 3
}
```

## Configuration

The application reads these settings from environment variables:

| Variable | Description |
| --- | --- |
| `AWS_REGION` | AWS region containing the S3 bucket and Bedrock resources. |
| `KB_ID` | Amazon Bedrock Knowledge Base ID. |
| `DS_ID` | Knowledge Base data source ID, used by the ingestion operation. |
| `BEDROCK_MODEL_NAME` | Bedrock generation model ID. Defaults to `amazon.nova-micro-v1:0`. |

The current S3 bucket and key prefix are set in `aws_s3.py`. Configure them for your own environment before using the application.

Do not commit AWS access keys or secret keys. For local development, use an AWS CLI profile or another supported AWS credential provider. On EKS, use EKS Pod Identity to provide temporary credentials to the application pod.

## Current ingestion behavior

The upload endpoint currently writes a file to S3, but the call that starts a Knowledge Base ingestion job is commented out in `main.py`. Therefore, uploading a file does not currently start ingestion automatically. Trigger a data source sync separately in the AWS console, or enable an appropriate ingestion workflow before expecting newly uploaded files to appear in search results.

## Run locally

1. Install Python dependencies from `requirements.txt`.
2. Configure the environment variables above and AWS credentials using a supported credential provider.
3. Start the API with Uvicorn:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```

4. Open `http://localhost:8080` or check `http://localhost:8080/health`.

The AWS identity used by the application needs permission for the S3 and Bedrock operations it performs. Bedrock model access and Knowledge Base setup must also be configured in the selected AWS region.

## Build the container

From the repository root:

```bash
docker build -t cookbook-rag .
docker run --rm -p 8080:8080 \
  -e AWS_REGION=<your-region> \
  -e KB_ID=<your-knowledge-base-id> \
  -e DS_ID=<your-data-source-id> \
  cookbook-rag
```

The container needs AWS credentials through a supported AWS credential provider. Do not bake credentials into the image. In production on EKS, use EKS Pod Identity rather than static access keys.

## Deployment

The `cookbook-rag-aws/` directory contains the Helm chart. The intended deployment flow is to build and push the container image to Amazon ECR, then deploy the chart to Amazon EKS with environment-specific settings and an EKS Pod Identity role. Review the chart values and align the configured Kubernetes service port with the container's port before deployment.
