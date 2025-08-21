# yourapp/utils/aws_utils.py

import boto3
from botocore.client import Config  # ✅ Import Config
from botocore.exceptions import ClientError
from django.conf import settings

def generate_presigned_url(file_key, expiration=3600):
    """
    Generates a pre-signed URL to get an object from S3.
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4')  # ✅ Force SigV4
    )
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': file_key,
            },
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None
