from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib.auth.views import login, logout
from meetingtools.settings import ADMIN_MEDIA_ROOT, MEDIA_ROOT
from meetingtools.multiresponse import redirect_to
admin.autodiscover()

def welcome(request):
    return redirect_to('/rooms')

urlpatterns = patterns('',
    (r'^$',welcome),
    (r'^admin-media/(?P<path>.*)$',                 'django.views.static.serve',{'document_root': ADMIN_MEDIA_ROOT}),
    (r'^site-media/(?P<path>.*)$',                  'django.views.static.serve',{'document_root': MEDIA_ROOT}),
    # Login/Logout
    (r'^accounts/login/?$','meetingtools.apps.auth.views.login'),
    (r'^accounts/login-federated/$','meetingtools.apps.auth.views.accounts_login_federated'),
    (r'^accounts/logout/$','meetingtools.apps.auth.views.logout'),
    (r'^rooms?$','meetingtools.apps.room.views.list'),
    (r'^rooms/(.+)(?:\.([^\.]+))?$','meetingtools.apps.room.views.rooms_by_group'),
    (r'^go/(\d+)$','meetingtools.apps.room.views.go_by_id'),
    (r'^go/(.+)$','meetingtools.apps.room.views.go_by_path'),
    (r'^room/create$','meetingtools.apps.room.views.create'),
    (r'^room/(\d+)$','meetingtools.apps.room.views.view'),
    (r'^room/(\d+)/modify$','meetingtools.apps.room.views.update'),
    (r'^room/(\d+)/delete$','meetingtools.apps.room.views.delete'),
    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    
    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls))
)
