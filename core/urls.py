from django.urls import path, include,re_path
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()


urlpatterns = [



    
    path('jobs/<str:job_id>/analyze-resumes/', views.analyze_resumes_view, name='job-analyze-resumes'),



    


    # API routes
    path('', include(router.urls)),
]
