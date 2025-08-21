from django.urls import path, include,re_path
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'admin', views.AdminViewSet)

urlpatterns = [
    
    
    
    path('users/dashboard/', views.UserViewSet.as_view({'get': 'dashboard_data'}), name='dashboard-data'),
    
    path('hr/dashboard/', views.HRViewSet.as_view({'get': 'hr_dashboard'}), name='hr-dashboard'),
    
    
    
    # Authentication
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    path('auth/google-login/', views.google_login_view, name='google-login'),

    path('company/<str:pk>/', views.company_detail_view, name='company-detail'),
    
    
    path('contact', views.contact_view, name='contact'),

    
    path('jobs/post/', views.post_job_view, name='post-job'),  # HR only
    path('jobs/<str:job_id>/apply/', views.apply_to_job, name='apply-job'),
    path('jobs/all/', views.all_jobs_view, name='all-jobs'),  # Admin only
    path('jobs/created/all', views.all_jobs_created_view, name='all-jobs'),  # hr only
    path('jobs/created/edit/<str:job_id>/', views.edit_created_job_view, name='edit-job'),# hr only
    path('jobs/created/delete/<str:job_id>/', views.delete_created_job_view, name='delete-job'),# hr and admin only
    
    
    path('jobs/<str:job_id>/applications/', views.specific_job_applications_view, name='job-applications'),


    
    path('jobs/<str:job_id>/analyze-resumes/', views.analyze_resumes_view, name='job-analyze-resumes'),


    path('applications/hr/', views.all_hr_applications_view, name='hr-all-applications'), # HR only
    path('hr/users', views.all_hr_user_view, name='hr-all-users'), # HR only
    

    
    
    path('applications/<str:application_id>/update-status/', views.update_application_status, name='update_application_status'),



    
    path('users/profile/', views.UserViewSet.as_view({'get': 'profile'}), name='user-profile'),
    path('users/change-password/', views.UserViewSet.as_view({'patch': 'change_password'}), name='change-password'),
    path('users/profile/edit/', views.UserViewSet.as_view({'patch': 'edit_profile'}), name='user-profile-edit'),

    # path('users/companies-list/', views.UserViewSet.as_view({'get': 'profile'}), name='user-profile'),
    path('users/companies-list/', views.UserViewSet.as_view({'get': 'companies_list'}), name='companies-list'),

    path('users/upload-resume/', views.UserViewSet.as_view({'post': 'upload_resume'}), name='user-upload-resume'),
    path('users/upload-profile-image/', views.UserViewSet.as_view({'post': 'upload_profile_image'}), name='upload-profile-image'),
    path('users/subscribe/', views.UserViewSet.as_view({'post': 'subscribe'}), name='user-subscribe'),
    
    # urls.py
    path('users/generate-payment-link/', views.UserViewSet.as_view({'post': 'generate_payment_link'}), name='generate-payment-link'),
    # path('users/razorpay-subscribe/',views.UserViewSet.as_view({'post': 'razorpay_subscribe'}), name='user-subscribe'),
    # path('users/payment-handler/', views.UserViewSet.as_view({'get': 'payment_handler'}), name='payment-handler'),
    path('users/confirm-subscription-payment/', views.UserViewSet.as_view({'post': 'confirm_subscription_payment'}), name='confirm-subscription-payment'),


    
    
    # path('users/', views.UserViewSet.as_view({'get': 'list'}), name='users-list'),  # Admin sees all, others see self
    path('jobs/available/', views.available_jobs_view, name='available-jobs'),
    path('applications/applied/', views.my_applications_view, name='my-applications'),
    path('hr/users/all/', views.AdminViewSet.as_view({'get': 'users_all'}), name='admin-users-all'),


    
    path('admin/pending-verifications/', views.AdminViewSet.as_view({'get': 'pending_verifications'}), name='pending-verifications'),
    path('admin/verify-company/<str:pk>/', views.AdminViewSet.as_view({'post': 'verify_company'}), name='verify-company'),
    # 🔝 there we can use admin/verify-company/id and in raw body {"action": "approve"}

    path('admin/users/all/', views.AdminViewSet.as_view({'get': 'users_all'}), name='admin-users-all'),
    path('admin/admin-list/', views.AdminViewSet.as_view({'get': 'admin_list'}), name='admin-admin-list'),
    path('admin/companies/all/', views.AdminViewSet.as_view({'get': 'companies_all'}), name='admin-companies-all'),
    path('admin/jobs/all/', views.AdminViewSet.as_view({'get': 'jobs_all'}), name='admin-jobs-all'),
    path('admin/applications/', views.AdminViewSet.as_view({'get': 'all_applications'}), name='all-applications'),
    path('admin/contact-list/', views.AdminViewSet.as_view({'get': 'contact_list'}), name='admin-contact-list'),
    path('admin/edit-role/<str:pk>/', views.AdminViewSet.as_view({'patch': 'edit_user_role'}), name='edit-user-role'),
    path('admin/subscriptions/', views.AdminViewSet.as_view({'get': 'all_subscriptions'}), name='all-subscriptions'),


    
    # otp routes
    
    path('users/request-otp/', views.RequestOTP.as_view(), name='request-otp'),
    path('users/verify-otp/', views.VerifyOTP.as_view(), name='verify-otp'),
    path('users/reset-password/', views.ResetPassword.as_view(), name='reset-password'),
    
    
    
    # path("api/subscription/create/", views.CreateSubscriptionAPIView.as_view()),
    
    # path('stream-users/', views.users_all_stream, name='stream_users'),
    # path('stream-users/', views.AdminViewSet.as_view({'get': 'users_all_stream'}), name='view-stream'),
    
    
    # path('favicon.ico', views.favicon_view),

    
    # API routes
    path('', include(router.urls)),
]
