def get_redirect_url(role):
    if role == 'user':
        return '/job-seeker-dashboard'
    elif role == 'hr':
        return '/company-dashboard'
    elif role == 'admin':
        return '/admin-dashboard'
    return '/'

# utils/aws.py
import boto3
from django.conf import settings

from botocore.client import Config  # Make sure this import is present

def generate_presigned_url(key: str, expiration=3600):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,  # ✅ Required for Signature V4
        config=Config(signature_version='s3v4')  # ✅ Force SigV4
        
    )
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Presigned URL generation error: {e}")
        return None
