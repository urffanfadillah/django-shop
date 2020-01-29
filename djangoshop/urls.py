# import settings
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from django.contrib.auth.views import LoginView, LogoutView

from core.views import signup

urlpatterns = [
    path('admin/', admin.site.urls),
    # path signup
    path('signup/', signup, name='signup'),
    # path login
    path('login/', LoginView.as_view(), name='login'),
    # path logout
    path('logout/', LogoutView.as_view(), name='logout'),
    # path item_list
    path('', include('core.urls', namespace='core')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

