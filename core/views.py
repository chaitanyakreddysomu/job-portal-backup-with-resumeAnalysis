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
from .models import User, AdminUser,Job,JobApplication,Contact,UserSubscription
from django.utils import timezone
from .serializers import (
    UserRegistrationSerializer, UserSerializer, LoginSerializer,
    AdminUserSerializer,JobSerializer,JobApplicationSerializer,CompanySerializer,HrUserSerializer,
    ResetPasswordSerializer,RequestOTPSerializer,VerifyOTPSerializer,ChangePasswordSerializer,ContactSerializer,
    UserSubscriptionSerializer
)
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
@permission_classes([permissions.AllowAny])
def google_login_view(request):
    token_from_client = request.data.get('token')

    if not token_from_client:
        return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        CLIENT_ID = "117920625230-nt6koku002p7jb66h1t22uk3r5qd1dga.apps.googleusercontent.com"  # <-- Your actual client ID here
        idinfo = id_token.verify_oauth2_token(
            token_from_client,
            googleRequest.Request(),
            CLIENT_ID,
            clock_skew_in_seconds=10  # Add 10 seconds skew allowance
        )

        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')

        full_name = name
        username = email.split("@")[0]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'full_name': full_name,
                'image': picture,
                'role': 'user',
                'is_verified': 'approved',
            }
        )

        if not user.image and picture:
            user.image = picture
            user.save()

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Login successful',
            'token': token.key,
            'user': UserSerializer(user).data,
            'redirect_url': get_redirect_url(user.role)
        })

    except ValueError as e:
        return Response({'error': 'Invalid token', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
   
# Authentication Views
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'Registration successful' if user.role != 'hr' else 'Registration submitted for verification',
            'token': token.key,
            'user': UserSerializer(user).data,
            'redirect_url': get_redirect_url(user.role)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'Login successful',
            'token': token.key,
            'user': UserSerializer(user).data,
            'redirect_url': get_redirect_url(user.role)
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout_view(request):
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def contact_view(request):

    data = request.data.copy()
    data['id'] = data.get('id') or str(uuid.uuid4().hex[:20])

    serializer = ContactSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Contact form submitted successfully.',
            'contact': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# def get_redirect_url(role):
#     role_urls = {
#         'user': '/dashboard/jobseeker',
#         'hr': '/dashboard/company', 
#         'admin': '/dashboard/admin'
#     }
#     return role_urls.get(role, '/dashboard')

# ViewSets
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser,JSONParser]
    
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return User.objects.all().order_by('-created_at')
        else:
            return User.objects.filter(id=self.request.user.id)
        
        

        
    @action(detail=False, methods=['get'], url_path='dashboard-data')
    def dashboard_data(self, request):
        user = request.user
        
        user_data = self.get_serializer(user).data
        available_jobs = Job.objects.filter(status='active').order_by('-created_at')[:5]
        available_jobs_data = JobSerializer(available_jobs, many=True).data
        
        recent_apps = JobApplication.objects.filter(applied_by=user).order_by('-applied_on')[:5]
        recent_apps_data = JobApplicationSerializer(recent_apps, many=True).data
        
        # Parse user skills string to list
        user_skills_list = []
        if user.skills:
            user_skills_list = [skill.strip().lower() for skill in user.skills.split(',') if skill.strip()]
        
        # Get job IDs user has applied for
        applied_job_ids = JobApplication.objects.filter(applied_by=user).values_list('job_id', flat=True)
        
        # Filter recommended jobs manually by checking skills overlap
        recommended_jobs_qs = Job.objects.filter(status='active').exclude(id__in=applied_job_ids).order_by('-created_at')
        
        recommended_jobs_filtered = []
        for job in recommended_jobs_qs:
            if not job.skills:
                continue
            job_skills_list = [skill.strip().lower() for skill in job.skills.split(',') if skill.strip()]
            if set(user_skills_list) & set(job_skills_list):  # check intersection
                recommended_jobs_filtered.append(job)
            if len(recommended_jobs_filtered) >= 5:
                break
        
        recommended_jobs_data = JobSerializer(recommended_jobs_filtered, many=True).data
        
        data = {
            "user_profile": user_data,
            "available_jobs": available_jobs_data,
            "recent_applications": recent_apps_data,
            "recommended_jobs": recommended_jobs_data,
        }
        
        return Response(data)


    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='companies-list')
    def companies_list(self, request):
        companies = User.objects.filter(role='hr').order_by('-created_at')
        serializer = self.get_serializer(companies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'], url_path='profile/edit')
    def edit_profile(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": "Profile updated successfully.",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=['patch'], url_path='change-password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(current_password):
            return Response({"detail": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

    

    @action(detail=False, methods=['post'], url_path='upload-resume')
    def upload_resume(self, request):
        user = request.user

        if user.role != 'user':
            return Response({"detail": "Only job seekers can upload resumes."}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('resume')
        if not file:
            return Response({"detail": "No resume file provided."}, status=status.HTTP_400_BAD_REQUEST)

        s3 = boto3.client('s3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME)

        # Delete previous resume if exists
        # if user.resume_key:
        #     try:
        #         s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=user.resume_key)
        #     except Exception as e:
        #         print("Resume deletion failed:", e)

        # Upload new resume
        resume_key = f"resumes/resume_{uuid.uuid4().hex}.pdf"
        try:
            s3.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                resume_key,
                ExtraArgs={'ContentType': file.content_type}
            )
        except Exception as e:
            return Response({"detail": "Resume upload failed.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Generate a pre-signed URL
        try:
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': resume_key},
                ExpiresIn=3600  # 1 hour
            )
        except ClientError as e:
            return Response({"detail": "Failed to generate pre-signed URL.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save the full pre-signed URL in resume field, and also store key if needed
        user.resume = presigned_url
        user.resume_key = resume_key  # optional: keep this if you want to track the key separately
        user.save()

        return Response({
            "detail": "Resume uploaded successfully.",
            "resume_url": presigned_url
        }, status=status.HTTP_200_OK)

        
        
    @action(detail=False, methods=['get'], url_path='resume-url')
    def get_resume_url(self, request):
        user = request.user

        if not user.resume_key:
            return Response({"detail": "No resume uploaded."}, status=status.HTTP_404_NOT_FOUND)

        s3 = boto3.client('s3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME)

        try:
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': user.resume_key},
                ExpiresIn=3600
            )
        except ClientError as e:
            return Response({"detail": "Failed to generate pre-signed URL.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "resume_url": presigned_url
        }, status=status.HTTP_200_OK)




    @action(detail=False, methods=['post'], url_path='upload-profile-image')
    def upload_profile_image(self, request):
        user = request.user
        file = request.FILES.get('image')

        if not file:
            return Response({"detail": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete previous image if it exists
        if user.image:
            try:
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                key = user.image.split(f"{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/")[-1]
                s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            except Exception as e:
                print("Image deletion failed:", e)

        # Upload new image
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        image_key = f"profile_images/profile_{uuid.uuid4().hex}.{file.name.split('.')[-1]}"
        try:
            s3.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                image_key,
                ExtraArgs={'ContentType': file.content_type}
            )
        except Exception as e:
            return Response({"detail": "Image upload failed.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{image_key}"
        user.image = image_url
        user.save()

        return Response({
            "detail": "Profile image uploaded successfully.",
            "image_url": image_url
        }, status=status.HTTP_200_OK)
        
        
        
    @action(detail=False, methods=['post'], url_path='subscribe')
    def subscribe(self, request):
        user = request.user
        new_plan = request.data.get('plan')

        if new_plan not in dict(User.PLAN_CHOICES):
            return Response({"detail": "Invalid plan selected."}, status=status.HTTP_400_BAD_REQUEST)

        # Only update if plan is different
        if user.plan != new_plan:
            user.plan = new_plan
            user.subscribe_date = timezone.now()
            user.save()
            return Response({
                "detail": f"Subscription updated to {new_plan}.",
                "plan": user.plan,
                "subscribe_date": user.subscribe_date
            }, status=status.HTTP_200_OK)
        
        return Response({"detail": "You are already subscribed to this plan."}, status=status.HTTP_200_OK)
    


    @action(detail=False, methods=['post'], url_path='generate-payment-link')
    def generate_payment_link(self, request):
        user = request.user
        if user.role != 'user':
            return Response({"detail": "Only job seekers can initiate payment."}, status=status.HTTP_403_FORBIDDEN)

        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({"detail": "plan_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            subscription_data = {
                "plan_id": plan_id,
                "total_count": 12,
                "customer_notify": 1,
                "notes": {"user_id": str(user.id), "user_email": user.email}
            }
            subscription = client.subscription.create(data=subscription_data)

            return Response({
                "subscription_id": subscription["id"],
                "plan_id": subscription["plan_id"],
                "subscription_link": subscription.get("short_url"),  # Razorpay's hosted link
                "customer_id": subscription.get("customer_id"),
                "next_due_on": subscription.get("current_end") or subscription.get("charge_at"),
                "created_at": subscription.get("created_at"),
                "status": subscription.get("status"),
                "razorpay_key": settings.RAZORPAY_KEY_ID,  # 🔑 Include Razorpay public key
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": "Subscription link creation failed.", "error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
            
            # 🔝 this working
            

    @action(detail=False, methods=['post'], url_path='confirm-subscription-payment')
    def confirm_subscription_payment(self, request):
        user = request.user
        data = request.data

        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_subscription_id = data.get('razorpay_subscription_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_payment_id, razorpay_subscription_id, razorpay_signature]):
            return Response({"detail": "Missing payment information."}, status=status.HTTP_400_BAD_REQUEST)

        # Manually verify signature
        if not verify_signature(
            razorpay_payment_id,
            razorpay_subscription_id,
            razorpay_signature,
            settings.RAZORPAY_KEY_SECRET
        ):
            return Response({"detail": "Invalid payment signature."}, status=status.HTTP_400_BAD_REQUEST)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            subscription_details = client.subscription.fetch(razorpay_subscription_id)
        except Exception as e:
            return Response({
                "detail": "Failed to fetch subscription details.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        plan_id = subscription_details.get('plan_id')
        plan_amount = 0
        plan_name = ''

        if plan_id:
            try:
                plan_details = client.plan.fetch(plan_id)
                plan_amount = plan_details.get('amount', 0)  # amount is in paise
                plan_name = plan_details.get('item', {}).get('name', '')
            except Exception:
                plan_amount = 0
                plan_name = ''

        sub_obj, created = UserSubscription.objects.get_or_create(
            user=user,
            razorpay_subscription_id=razorpay_subscription_id,
            defaults={
                'plan_name': plan_name,
                'plan_amount': plan_amount / 100,  # paise to INR
                'subscribe_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30 * 12),
                'next_renewal_date': timezone.now() + timedelta(days=30),
            }
        )

        # ✅ Update user model as well
        user.plan = plan_name
        user.subscribe_date = timezone.now()
        user.save()

        return Response({
            "detail": "Subscription verified and saved successfully.",
            "subscription": UserSubscriptionSerializer(sub_obj).data
        }, status=status.HTTP_200_OK)

class AdminViewSet(viewsets.ModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]

    @action(detail=False, methods=['get'])
    def pending_verifications(self, request):
        pending_users = User.objects.filter(role='hr', is_verified='pending')
        serializer = UserSerializer(pending_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_subscriptions(self, request):
        subscriptions = UserSubscription.objects.all()
        serializer = UserSubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify_company(self, request, pk=None):
        """
        Approve or Reject HR Company Account
        POST body: { "action": "approve" } or { "action": "reject" }
        """
        action_type = request.data.get('action')  # 'approve' or 'reject'

        try:
            user = User.objects.get(pk=pk, role='hr')
        except User.DoesNotExist:
            return Response({'error': 'Company user not found'}, status=status.HTTP_404_NOT_FOUND)

        if action_type == 'approve':
            user.is_verified = 'approved'
        elif action_type == 'reject':
            user.is_verified = 'rejected'
        else:
            return Response({'error': 'Invalid action. Must be approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)

        user.save()
        return Response({'message': f'Company {action_type}d successfully'})

    @action(detail=False, methods=['get'])
    def users_all(self, request):
        users = User.objects.filter(role='user')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    # @action(detail=False, methods=['get'])
    # def users_all_stream(self, request):
    #     def user_generator():
    #         users = User.objects.filter(role='user')
    #         for user in users.iterator():
    #             serializer = UserSerializer(user)
    #             yield json.dumps(serializer.data) + '\n'
    #             time.sleep(1)

    #     return StreamingHttpResponse(user_generator(), content_type='application/x-ndjson')

    @action(detail=False, methods=['get'])
    def companies_all(self, request):
        companies = User.objects.filter(role='hr')
        serializer = UserSerializer(companies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def admin_list(self, request):
        admins = User.objects.filter(role='admin')
        serializer = UserSerializer(admins, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def jobs_all(self, request):
        jobs = Job.objects.all().order_by('-created_at')
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def all_applications(self, request):
        applications = JobApplication.objects.all().select_related('job', 'applied_by', 'job__created_by')
        serializer = JobApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], url_path='edit-role', permission_classes=[IsAdmin])
    def edit_user_role(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get('role')
        valid_roles = ['user', 'admin']

        if new_role not in valid_roles:
            return Response({'error': f"Invalid role. Choose from {valid_roles}."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.role = new_role
        user.save()
        return Response({'message': f"User role updated to '{new_role}'"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='contact-list')
    def contact_list(self, request):
        contacts = Contact.objects.all().order_by('-created_at')  # Optional ordering
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_job_view(request):
    user = request.user

    # Only HR users can post
    if user.role != 'hr':
        return Response({'detail': 'Only HR users can post jobs.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = JobSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def apply_to_job(request, job_id):
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    # Prevent duplicate application
    if JobApplication.objects.filter(job=job, applied_by=user).exists():
        return Response({"error": "You have already applied to this job."}, status=status.HTTP_400_BAD_REQUEST)
    application = JobApplication.objects.create(
        job=job,
        name=user.full_name,
        role=job.job_type,
        applied_by=user,
        resume_url=user.resume_key, 
        applied_on=timezone.now(),
    )

    job.application_count += 1
    job.save()

    return Response({
        "message": "Application submitted successfully.",
        "application_id": application.application_id
    }, status=status.HTTP_201_CREATED)
    
    
# update status of application
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .models import JobApplication



@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_application_status(request, application_id):
    try:
        application = JobApplication.objects.select_related('job', 'applied_by', 'job__created_by').get(application_id=application_id)
    except JobApplication.DoesNotExist:
        return Response({"error": "Application not found"}, status=404)

    user = request.user

    # Only the HR who posted the job OR an admin can update status
    if user != application.job.created_by and user.role != 'admin':
        return Response({"error": "You are not authorized to update this application"}, status=403)

    new_status = request.data.get('status')
    if new_status not in dict(JobApplication.STATUS_CHOICES):
        return Response({"error": "Invalid status"}, status=400)

    old_status = application.status
    application.status = new_status
    application.save()

    # ✅ Send email only if status has changed
    if old_status != new_status:
        send_status_update_email(application, old_status, new_status)

    return Response({
        "message": "Status updated successfully",
        "status": application.get_status_display()
    }, status=200)

def send_status_update_email(application,old_status, new_status):
    user = application.applied_by
    job = application.job
    status_display = new_status.replace('_', ' ').title()
    if new_status == 'under_review':
        message_body = f"Your application for {job.title} is currently under review."
    elif new_status == 'interview_scheduled':
        message_body = f"Your application for {job.title} is under review. Please wait for the interview call."
    elif new_status == 'rejected':
        message_body = f"We're sorry to inform you that your application for {job.title} has been rejected. Please explore more jobs on our platform."
    elif new_status == 'hired':
        message_body = f"🎉 Congratulations! You have been selected for the role of {job.title} at {job.created_by.company_name}."
    else:
        message_body = f"Your application status has been updated to {status_display}."

    # subject = f"Your Job Application Status Changed to '{new_status.title().replace('_', ' ')}'"
    subject = f"Your Job Application Status `{job.title}` at `{job.created_by.company_name}`" 
    message = f"""
Hi {user.username},

{message_body}

Thank you for choosing incircleJobs.

Best,
Recruitment Team
"""

    send_mail(
        subject,
        message.strip(),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
   

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_jobs_view(request):
    if request.user.role != 'admin':
        return Response({"error": "Only admins can view all jobs."}, status=403)

    jobs = Job.objects.all().order_by('-created_at')
    serializer = JobSerializer(jobs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_jobs_created_view(request):
    if request.user.role != 'hr':
        return Response(
            {"error": "Access denied. Only HRs can view their posted jobs."},
            status=status.HTTP_403_FORBIDDEN
        )

    jobs = Job.objects.filter(created_by=request.user).order_by('-created_at')
    serializer = JobSerializer(jobs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_created_job_view(request, job_id):  # job_id is a string (UUID or slug)
    if request.user.role != 'hr':
        return Response(
            {"error": "Access denied. Only HRs can edit job posts."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        job = Job.objects.get(id=job_id, created_by=request.user)
    except Job.DoesNotExist:
        return Response(
            {"error": "Job not found or you're not authorized to edit this job."},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = JobSerializer(job, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_created_job_view(request, job_id):
    # Only HRs and Admins can delete job posts
    if request.user.role not in ['hr', 'admin']:
        return Response(
            {"error": "Access denied. Only HRs and Admins can delete job posts."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        if request.user.role == 'admin':
            # Admins can delete any job
            job = Job.objects.get(id=job_id)
        else:
            # HRs can only delete jobs they created
            job = Job.objects.get(id=job_id, created_by=request.user)
    except Job.DoesNotExist:
        return Response(
            {"error": "Job not found or you're not authorized to delete this job."},
            status=status.HTTP_404_NOT_FOUND
        )

    job.delete()  # Related applications will be deleted due to on_delete=models.CASCADE
    return Response({"message": "Job and related applications deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



@api_view(['GET'])
@permission_classes([AllowAnyPermission])  # or use IsAuthenticated if you want only logged-in users
def available_jobs_view(request):
    jobs = Job.objects.filter(status='active').order_by('-created_at')
    serializer = JobSerializer(jobs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_applications_view(request):
    user = request.user
    applications = JobApplication.objects.filter(applied_by=user).order_by('-applied_on')
    serializer = JobApplicationSerializer(applications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def all_hr_applications_view(request):
    user = request.user

    # Only HRs can access this
    if user.role != 'hr':
        return Response({"error": "Only HRs can access this."}, status=403)

    # Fetch applications for jobs created by this HR
    applications = JobApplication.objects.filter(job__created_by=user).order_by('-applied_on')
    serializer = JobApplicationSerializer(applications, many=True)
    return Response(serializer.data, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def specific_job_applications_view(request, job_id: str) -> Response:
    user = request.user

    # Ensure only HR users can access
    if user.role != 'hr':
        return Response({"error": "Only HRs can access this."}, status=403)

    # Get the job and ensure it belongs to the logged-in HR user
    job = get_object_or_404(Job, id=job_id, created_by=user)

    # Fetch applications related to this job
    applications = JobApplication.objects.filter(job=job).order_by('-applied_on')
    serializer = JobApplicationSerializer(applications, many=True)
    return Response(serializer.data, status=200)

# import requests

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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def all_hr_user_view(request):
    user = request.user

    # Only HRs can access this
    if user.role != 'hr':
        return Response({"error": "Only HRs can access this."}, status=403)

    # Fetch applications for jobs created by this HR
    users = User.objects.filter(role='user')
    serializer = HrUserSerializer(users, many=True)
    return Response(serializer.data, status=200)





@api_view(['GET'])
@permission_classes([AllowAnyPermission])  # Change to IsAuthenticated if needed
def company_detail_view(request, pk):
    try:
        company = User.objects.get(id=pk, role='hr')
        serializer = CompanySerializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)


# otp 

User = get_user_model()


def generate_otp():
    return str(random.randint(100000, 999999))




from django.core.mail import EmailMessage
from django.conf import settings

class RequestOTP(APIView):
    permission_classes = [AllowAnyPermission]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'error': 'Email not registered.'}, status=404)

            otp = generate_otp()
            cache.set(f'otp_{email}', otp, timeout=600)
            otp_formatted = f"{otp[:3]} - {otp[3:]}"

            subject = 'Verify Your Email - OTP Inside'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [email]

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 0; margin: 0;">
              <div style="max-width: 600px; background-color: #ffffff; border-radius: 8px; padding: 20px; margin: 30px auto; box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);">
                <div style="text-align: center;">
                  

                  <div style="background: #144fa9db; padding: 30px; border-radius: 4px; color: #fff; font-size: 20px; margin: 20px 0px;">
                    <div style="font-size: 30px; font-weight: 800; margin: 7px 0px;">Incirclejobs</div>
                    <div style="margin-top: 25px; font-size: 25px; letter-spacing: 3px;">Reset Your Password</div>

                    
                  </div>
                  <h2>Hello, {user.first_name or user.email}</h2>
                  <p>Your One-Time Password (OTP) for Password Reset is:</p>
                  <div style="font-size: 24px; font-weight: bold; background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 8px; border: 1px dashed #007bff; color: #007bff;"> {otp_formatted}</div>
                  <p style="margin-top: 20px;">
                Please use this OTP to complete your verification. The OTP is valid for the next 10 minutes.
                </p>

                </div>
                <div style="color: #6c757d; font-size: 14px; text-align: center; margin-top: 20px;">
                  <p>Thank you,<br>The Incirclejobs Team</p>
                </div>
              </div>
            </body>
            </html>
            """

            email_message = EmailMessage(subject, html_content, from_email, to_email)
            email_message.content_subtype = "html"
            email_message.send()

            return Response({'message': 'OTP sent to email.'})

        return Response(serializer.errors, status=400)

class VerifyOTP(APIView):
    permission_classes = [AllowAnyPermission]  # ✅ Allow unauthenticated access
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            cached_otp = cache.get(f'otp_{email}')
            if cached_otp == otp:
                cache.set(f'verified_{email}', True, timeout=600)
                return Response({'message': 'OTP verified.'})
            return Response({'error': 'Invalid or expired OTP.'}, status=400)
        return Response(serializer.errors, status=400)


class ResetPassword(APIView):
    permission_classes = [AllowAnyPermission]  # ✅ Allow unauthenticated access
    def patch(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']

            if not cache.get(f'verified_{email}'):
                return Response({'error': 'OTP not verified or expired.'}, status=400)

            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()

                cache.delete(f'otp_{email}')
                cache.delete(f'verified_{email}')

                return Response({'message': 'Password reset successfully.'})
            except User.DoesNotExist:
                return Response({'error': 'User not found.'}, status=404)
        return Response(serializer.errors, status=400)
    
    
    
# from rest_framework import viewsets, status, permissions
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# from django.utils import timezone
# from django.conf import settings
# from botocore.exceptions import ClientError
# import boto3
# import uuid

# from .models import User, Job, JobApplication
# from .serializers import UserSerializer, JobSerializer, JobApplicationSerializer, HrUserSerializer, ChangePasswordSerializer


class HRViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['dashboard', 'post_job', 'edit_job', 'delete_job', 'job_applications', 'user_list']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def _is_hr(self, user):
        return user.role == 'hr'

    @action(detail=False, methods=['get'], url_path='hr-dashboard')
    def hr_dashboard(self, request):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HR users can access dashboard."}, status=403)

        # HR Profile
        user_profile_data = UserSerializer(user).data

        # All Jobs Posted by HR (renamed to posted_jobs)
        posted_jobs = Job.objects.filter(created_by=user).order_by('-created_at')
        posted_jobs_data = JobSerializer(posted_jobs, many=True).data

        # Recent Applications Received for HR's Jobs
        recent_applications = JobApplication.objects.filter(
            job__created_by=user
        ).order_by('-applied_on')[:10]
        Job_applications_data = JobApplicationSerializer(recent_applications, many=True).data

        response_data = {
            "user_profile": user_profile_data,
            "posted_jobs": posted_jobs_data,
            "Job_applications": Job_applications_data,
            # "recommended_jobs": []  # Add matching jobs later if needed
        }

        return Response(response_data, status=200)

    @action(detail=False, methods=['post'], url_path='post-job')
    def post_job(self, request):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HRs can post jobs."}, status=403)

        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'], url_path='jobs')
    def all_jobs(self, request):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HRs can view jobs."}, status=403)

        jobs = Job.objects.filter(created_by=user).order_by('-created_at')
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], url_path='edit-job/(?P<job_id>[^/.]+)')
    def edit_job(self, request, job_id):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HRs can edit jobs."}, status=403)

        try:
            job = Job.objects.get(id=job_id, created_by=user)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found or unauthorized."}, status=404)

        serializer = JobSerializer(job, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['delete'], url_path='delete-job/(?P<job_id>[^/.]+)')
    def delete_job(self, request, job_id):
        user = request.user
        if user.role not in ['hr', 'admin']:
            return Response({"detail": "Unauthorized."}, status=403)

        try:
            job = Job.objects.get(id=job_id)
            if user.role == 'hr' and job.created_by != user:
                return Response({"detail": "Not allowed to delete this job."}, status=403)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=404)

        job.delete()
        return Response({"detail": "Job deleted successfully."}, status=204)

    @action(detail=False, methods=['patch'], url_path='update-application-status/(?P<application_id>[^/.]+)')
    def update_application_status(self, request, application_id):
        user = request.user

        try:
            application = JobApplication.objects.select_related('job').get(application_id=application_id)
        except JobApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=404)

        if user != application.job.created_by and user.role != 'admin':
            return Response({"detail": "Not authorized to update this application."}, status=403)

        new_status = request.data.get('status')
        if new_status not in dict(JobApplication.STATUS_CHOICES):
            return Response({"detail": "Invalid status."}, status=400)

        application.status = new_status
        application.save()
        return Response({"message": "Status updated.", "status": application.get_status_display()})

    @action(detail=False, methods=['get'], url_path='applications')
    def job_applications(self, request):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HRs can view applications."}, status=403)

        applications = JobApplication.objects.filter(job__created_by=user).order_by('-applied_on')
        serializer = JobApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    

    # @action(detail=True, methods=["post"], url_path="analyze-resumes")
    # def analyze_resumes(self, request, pk=None):
    #     job = self.get_object()
    #     jd = job.description
    #     applications = JobApplication.objects.filter(job=job)
        
    #     if not applications.exists():
    #         return Response({"detail": "No applications found for this job."}, status=404)

    #     results = []

    #     for app in applications:
    #         resume_url = app.resume_url  # Assuming resumes are stored in S3 and URL is saved here
            
    #         if not resume_url:
    #             results.append({
    #                 "application_id": app.application_id,
    #                 "name": app.name,
    #                 "status": app.status,
    #                 "match": "Resume missing",
    #                 "note": "No resume URL found."
    #             })
    #             continue

    #         try:
    #             # Download the PDF from S3
    #             response = requests.get(resume_url)
    #             response.raise_for_status()

    #             # Save to temp file
    #             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
    #                 tmp_file.write(response.content)
    #                 resume_path = tmp_file.name

    #             # Extract & analyze
    #             text = extract_text_from_pdf(resume_path)
    #             is_resume, note, has_negatives = looks_like_resume(text)

    #             if not is_resume:
    #                 results.append({
    #                     "application_id": app.application_id,
    #                     "name": app.name,
    #                     "status": app.status,
    #                     "match": "Not a valid resume",
    #                     "note": note
    #                 })
    #                 continue

    #             percent = sbert_similarity_percent(jd, text)
    #             if has_negatives:
    #                 percent = max(0, percent - 10)

    #             label = "Strong match" if percent >= 70 else "Moderate match" if percent >= 50 else "Weak match"

    #             results.append({
    #                 "application_id": app.application_id,
    #                 "name": app.name,
    #                 "status": app.status,
    #                 "match": label,
    #                 "score": percent
    #             })

    #         except Exception as e:
    #             results.append({
    #                 "application_id": app.application_id,
    #                 "name": app.name,
    #                 "status": app.status,
    #                 "match": "Error",
    #                 "note": str(e)
    #             })

    #         finally:
    #             if os.path.exists(resume_path):
    #                 os.remove(resume_path)

    #     return Response(results)


    @action(detail=False, methods=['get'], url_path='users')
    def user_list(self, request):
        user = request.user
        if not self._is_hr(user):
            return Response({"detail": "Only HRs can view users."}, status=403)

        users = User.objects.filter(role='user')
        serializer = HrUserSerializer(users, many=True)
        return Response(serializer.data)
 

from django.http import StreamingHttpResponse
from rest_framework.renderers import JSONRenderer
import json

 
