from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, AdminUser,Job,JobApplication,Contact,UserSubscription
from django.db import models
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
from .utils import generate_presigned_url

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password', 'full_name',
            'phone', 'role', 'skills', 'experience', 'company_name',
            'location',
            'company_description', 'website'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        
        role = attrs.get('role')
        
        if role == 'hr':
            if not attrs.get('company_name'):
                raise serializers.ValidationError("Company name is required for HR role")
            if not attrs.get('company_description'):
                raise serializers.ValidationError("Company description is required for HR role")
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        # Set verification status based on role
        if validated_data.get('role') == 'hr':
            validated_data['is_verified'] = 'pending'
        else:
            validated_data['is_verified'] = 'approved'

        user = User.objects.create_user(password=password, **validated_data)
        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'image',
            'email',
            'full_name',
            'phone',
            'location',
            'role',
            'skills',
            'plan',
            'subscribe_date',
            'experience',
            'resume',
            'company_name',
            'company_description',
            'bio',
            'website',
            'is_verified',
            'created_at',
            'updated_at',
            'resume_key',
        ]

        read_only_fields = ['id', 'created_at', 'is_verified']
      
      
class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['resume']
               
class HrUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'phone',
            'location',
            'role',
            'skills',
            'experience',
            'resume',
            # 'company_name',
            # 'company_description',
            'bio',
            # 'website',
            # 'is_verified',
            # 'created_at',
            # 'updated_at'
        ]

        read_only_fields = ['id', 'created_at', 'is_verified']
        
        
UserModel = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()  # Will accept either username or email
    password = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs.get('username')  # Can be username or email
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError('Username/email and password are required')

        # Try to find user by username or email
        try:
            user = UserModel.objects.get(models.Q(username=identifier) | models.Q(email=identifier))
        except UserModel.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials')

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')

        if user.role == 'hr' and not user.is_verified:
            raise serializers.ValidationError('Your company account is pending admin verification')

        attrs['user'] = user
        return attrs

class AdminUserSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = AdminUser
        fields = '__all__'
        
class JobSerializer(serializers.ModelSerializer):
    created_by_id = serializers.CharField(source='created_by.id', read_only=True)
    company_name = serializers.CharField(source='created_by.company_name', read_only=True)
    created_by = serializers.CharField(source='created_by.id', read_only=True)

    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'company_name', 'company_description', 'website', 'is_verified']

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        
                
class JobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    applied_by = UserSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            'id',
            'application_id',
            'job',
            'job_title',
            'company_name',
            'name',
            'role',
            'applied_by',
            'applied_on',
            'status',
            'resume_url',
            'main_resume_url',  # optional if needed elsewhere
        ]
        read_only_fields = ['application_id', 'applied_on', 'applied_by']

    def get_resume_url(self, obj):
        if obj.resume_url:
            return generate_presigned_url(obj.resume_key)
        return None

    def get_job_title(self, obj):
        return obj.job.title if obj.job else None

    def get_company_name(self, obj):
        if obj.job and obj.job.created_by:
            return obj.job.created_by.company_name
        return None
    
                
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'is_verified']
        
        
# otp serializers

class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, min_length=6)
    

class ChangePasswordSerializer(serializers.Serializer): # change password from profile
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = '__all__'