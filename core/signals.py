from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User,Job



@receiver(post_save, sender=Job)
def notify_users_on_job_post(sender, instance, created, **kwargs):
    # print("🚨 Signal triggered for job:", instance.title) 
    if not created:
        return  # Only trigger on creation

    job_skills = [skill.strip().lower() for skill in instance.skills.split(',') if skill.strip()]
    
    if not job_skills:
        return

    # Get active job seekers with email
    users = User.objects.filter(role='user', is_active=True).exclude(email__isnull=True).exclude(email='')

    for user in users:
        if not user.skills:
            continue
        user_skills = [skill.strip().lower() for skill in user.skills.split(',') if skill.strip()]
        
        # Check for skill match
        if set(job_skills) & set(user_skills):
            subject = "New Job Matching Your Skills!"
            message =f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f7fafc; padding: 20px; color: #333;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 20px;">
          <h2 style="color: #1e40af; margin-bottom: 0.2em;">{instance.title}</h2>
          <p style="font-weight: 600; color: #4b5563; margin-top: 0;">{instance.created_by.company_name or 'N/A'}</p>
          
          <span style="display: inline-block; background-color: #bfdbfe; color: #1e40af; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: capitalize; margin-bottom: 16px;">
            {instance.job_type.replace('_', ' ')}
          </span>
          <span style="display: inline-block; background-color: #bfdbfe; color: #1e40af; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: capitalize; margin-bottom: 16px;">
            {instance.work_arrangement}
          </span>

          <p style="color: #4b5563; margin: 8px 0;">
            <strong>Location:</strong> {instance.location}<br/>
            <strong>Experience Level:</strong> {instance.experience_level}<br/>
            <strong>Posted On:</strong> {instance.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            
          </p>

          <p style="color: #374151; font-size: 14px; line-height: 1.5; margin-top: 16px;">
            {instance.description}
          </p>

          <div style="margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px;">
            <strong>Required Skills: </strong>{instance.skills}
          </div>

          <p style="margin-top: 20px; font-weight: 700; color: #16a34a; font-size: 16px;">
            {instance.currency} {instance.min_salary} - {instance.max_salary}
          </p>

          <p style="margin-top: 8px; font-weight: 600; color: #dc2626; font-size: 14px;">
            Apply before: {instance.application_deadline}
          </p>

          <a href="https://www.incirclejobs.com/job/{instance.id}" 
             style="
               display: inline-block;
               margin-top: 24px;
               background-color: #2563eb;
               color: white;
               padding: 12px 24px;
               text-decoration: none;
               border-radius: 6px;
               font-weight: 700;
               font-size: 14px;
               ">
            View Details & Apply
          </a>

          <p style="margin-top: 32px; font-size: 12px; color: #6b7280;">
            Best,<br/>
            Your IncircleJobs Team
          </p>
        </div>
      </body>
    </html>
    """
            send_mail(
    subject=subject,
    message="",  # plain text fallback (can be empty or a summary)
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[user.email],
    fail_silently=True,
    html_message=message  # <-- this sends the HTML
)

