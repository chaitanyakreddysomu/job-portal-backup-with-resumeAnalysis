from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static  # for serving media/static in development

from django.views.generic import RedirectView
from django.templatetags.static import static as static_url  # for generating static file URL


import os
from django.conf import settings
from django.http import FileResponse, Http404
    
def favicon_view(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'static', 'favicon.ico')
    if os.path.exists(favicon_path):
        return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')
    else:
        raise Http404()
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),

    # # Redirect /favicon.ico requests to the static favicon file (e.g., .jpg or .png)
    # re_path(r'^favicon\.ico$', RedirectView.as_view(
    #     url=static_url('favicon.ico'),  # <-- change to 'favicon.png' if needed
    #     permanent=True
    # )),

    path('favicon.ico', favicon_view),

]

# Serve static and media files during development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
