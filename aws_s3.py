import boto3
import logging
import os
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
# Configure logging to show INFO and above, with a helpful format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
session = boto3.Session()

AWS_REGION = os.environ.get("AWS_REGION")
s3_client = session.client(service_name="s3", region_name=AWS_REGION)
BUCKET_NAME = "vinod-cookbook"
BUCKET_KEY = "cookbook"

def put_file(file_content, filename):

    try:
        res = s3_client.put_object(
            Body=file_content,
            Bucket=BUCKET_NAME,
            Key=BUCKET_KEY+'/'+filename
        )
        return res["ResponseMetadata"]["HTTPStatusCode"]
    except ClientError as err:
        if err.response["Error"]["Code"] == "NoSuchBucket":
            logger.error(f"The {BUCKET_NAME} is not present in the aws.")