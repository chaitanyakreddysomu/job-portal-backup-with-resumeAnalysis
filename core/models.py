from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.conf import settings
from django.utils import timezone


import secrets
import string

def generate_custom_user_id():
    chars = string.ascii_letters + string.digits + "-_.~!$'()*@"
    random_id = ''.join(secrets.choice(chars) for _ in range(10))
    return f"user_{random_id}"



class User(AbstractUser):
    
    VERIFICATION_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ]
    # PLAN_CHOICES = [
    #     ('free', 'Free'),
    #     ('legend', 'Legend'),
    #     ('ultra-legend', 'Ultra Legend'),
    #     # add more plans as needed
    # ]
    id = models.CharField(
        primary_key=True,
        default=generate_custom_user_id,
        editable=False,
        max_length=20,
        unique=True
    )
    ROLE_CHOICES = [
        ('user', 'Job Seeker'),
        ('hr', 'Company/HR'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True) 
    # Inside your User model
    image = models.URLField(blank=True, null=True)

    resume = models.URLField(max_length=1000,blank=True, null=True)
    resume_key = models.CharField(max_length=255, blank=True, null=True)
    # Job Seeker specific fields
    skills = models.TextField(blank=True, null=True, help_text="Comma separated skills")
    experience = models.CharField(max_length=50, blank=True, null=True)
    # resume = models.FileField(upload_to='resumes/', blank=True, null=True)

    # resume = models.URLField(blank=True, null=True ,default="https://claude.ai/chat/2862ceeb-0272-42b6-8740-fb3855822d7d")
    location = models.TextField(blank=True, null=True,default="default location")
    plan = models.CharField(max_length=20, default='free')
    subscribe_date = models.DateTimeField(blank=True, null=True)
    
    # Company/HR specific fields
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_description = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True,default="i am a singer")
    website = models.URLField(blank=True, null=True)
    is_verified = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        db_table = 'users'





class AdminUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True)
    department = models.CharField(max_length=100, blank=True)
    permissions = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Admin: {self.user.username}"

def generate_custom_contact_id():
    chars = string.ascii_letters + string.digits + "-_.~!$'()*@"
    random_id = ''.join(secrets.choice(chars) for _ in range(10))
    return f"contact_{random_id}"

   
class Contact(models.Model):
    
    INQUIRY_TYPE = [
        ('general-inquiry', 'General Inquiry'),
        ('technical-support', 'Technical Support'),
        ('billing-question', 'Billing Question'),
        ('job-seeker-help', 'Job Seeker Help'),
        ('employer-support', 'Employer Support'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        
        # add more as needed
    ]
    id = models.CharField(
        primary_key=True,
        default=generate_custom_contact_id,
        editable=False,
        max_length=20,
        unique=True
    )
    # user = models.OneToOneField(User, on_delete=models.CASCADE,null=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField() 
    phone = models.CharField(max_length=15, blank=True, null=True)
    inquiry = models.CharField(max_length=100, choices=INQUIRY_TYPE)
    subject = models.CharField(max_length=255, blank=True)
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    
    def __str__(self):
        return f"Admin: {self.subject}" 
    
def generate_custom_job_id():
    chars = string.ascii_letters + string.digits + "-_.~!$'()*@"
    random_id = ''.join(secrets.choice(chars) for _ in range(10))
    return f"job_{random_id}"

class Job(models.Model):
    JOB_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    ]

    WORK_ARRANGEMENTS = [
        ('on_site', 'On-Site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]

    EXPERIENCE_LEVELS = [
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('INR', 'INR'),
        ('GBP', 'GBP'),
        # add more as needed
    ]

    id = models.CharField(
        primary_key=True,
        default=generate_custom_job_id,
        editable=False,
        max_length=20,
        unique=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255)
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    work_arrangement = models.CharField(max_length=50, choices=WORK_ARRANGEMENTS)
    experience_level = models.CharField(max_length=50)

    min_salary = models.DecimalField(max_digits=10, decimal_places=2)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES)

    description = models.TextField()
    responsibilities = models.TextField(help_text="List one responsibility per line")
    requirements = models.TextField(help_text="List one requirement per line")
    skills = models.TextField(help_text="Comma-separated skills")
    benefits = models.TextField(blank=True, null=True, help_text="List one benefit per line")

    application_deadline = models.DateField()
    is_urgent = models.BooleanField(default=False)
    is_remote = models.BooleanField(default=False)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    application_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.created_by.company_name})"
    class Meta:
        db_table = 'Jobs'
    
def generate_application_id():
    return f"app_{secrets.token_hex(6)}"  # Example: app_a1b2c3d4e5f6

class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]
    application_id = models.CharField(max_length=20, unique=True, default=generate_application_id)
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='applications')
    name = models.CharField(max_length=255,default="name")
    role = models.CharField(max_length=100)
    applied_by = models.ForeignKey('User', on_delete=models.CASCADE)
    applied_on = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    resume_url = models.CharField(max_length=255, null=True, blank=True) 
    main_resume_url = models.CharField(max_length=1000, null=True, blank=True) 

    def __str__(self):
        return f"{self.name} applied for {self.job.title}"
    
    
    @property
    def resume_key(self):
        # Assuming resume_url stores the key path (e.g., 'resumes/user123.pdf')
        return self.resume_url

    class Meta:
        db_table = 'Job_Applications'
    




def generate_custom_subscription_id():
    chars = string.ascii_letters + string.digits + "-_.~!$'()*@"
    random_id = ''.join(secrets.choice(chars) for _ in range(10))
    return f"pay_{random_id}"

class UserSubscription(models.Model):
    id = models.CharField(
        primary_key=True,
        default=generate_custom_subscription_id,
        editable=False,
        max_length=30,
        unique=True
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    razorpay_subscription_id = models.CharField(max_length=100, unique=True)
    plan_name = models.CharField(max_length=100)
    plan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    subscribe_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    next_renewal_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan_name}"
    
    
    