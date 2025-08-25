import boto3
import time
import os
import razorpay
import random
from botocore.exceptions import ClientError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import User,Job,JobApplication
from django.utils import timezone

from .utils import generate_presigned_url
from google.oauth2 import id_token
# from google.oauth2 import id_token
# from google.auth.transport import requests
import requests 
from google.auth.transport import requests as googleRequest

import hmac
from django.shortcuts import get_object_or_404
import hashlib
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from .utils import get_redirect_url
import uuid
from rest_framework.views import APIView
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
# from razorpay_client import client
from django.utils import timezone
from datetime import timedelta
import razorpay
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import HttpResponseBadRequest
from razorpay.errors import SignatureVerificationError
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
from django.http import StreamingHttpResponse
from .resume_analysis import (
    extract_metadata_text,
    looks_like_resume,
    sbert_similarity_percent,
    extract_text_from_pdf_bytes
)
import tempfile

def verify_signature(payment_id, subscription_id, signature, secret):
    msg = f"{payment_id}|{subscription_id}".encode()
    generated_signature = hmac.new(
        key=secret.encode(),
        msg=msg,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)
# Custom Permissions
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user

class IsHROrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['hr', 'admin']

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
class AllowAnyPermission(permissions.BasePermission):
    """
    Custom permission that always allows access.
    Equivalent to rest_framework.permissions.AllowAny
    """
    def has_permission(self, request, view):
        return True




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_resumes_view(request, job_id: str) -> Response:
    user = request.user

    if user.role != 'hr':
        return Response({"error": "Only HRs can access this."}, status=403)

    job = get_object_or_404(Job, id=job_id, created_by=user)
    applications = JobApplication.objects.filter(job=job)
    job_description = job.description or ""

    analysis_results = []

    for app in applications:
        if not app.resume_url:
            continue

        presigned_url = generate_presigned_url(app.resume_url)
        if not presigned_url:
            continue

        try:
            # ✅ Download PDF from S3
            response = requests.get(presigned_url)
            resume_bytes = response.content

            # ✅ Extract text from in-memory bytes
            resume_text = extract_text_from_pdf_bytes(resume_bytes)

            # ✅ Check if it's a valid resume
            is_resume, resume_note, has_neg = looks_like_resume(resume_text)

            if not is_resume:
                analysis_results.append({
                    'application_id': app.application_id,
                    'name': app.name,
                    'valid_resume': False,
                    'reason': resume_note,
                    'score': 0,
                    'resume_url': presigned_url,
                })
                continue

            # ✅ Calculate similarity
            similarity = sbert_similarity_percent(job_description, resume_text)
            if has_neg:
                similarity = max(0, similarity - 10)

            analysis_results.append({
                'application_id': app.application_id,
                'name': app.name,
                'valid_resume': True,
                'score': similarity,
                'resume_url': presigned_url,
            })

        except Exception as e:
            print(f"Error analyzing resume for {app.name}: {e}")
            continue

    return Response(analysis_results, status=200)

  
    



 
