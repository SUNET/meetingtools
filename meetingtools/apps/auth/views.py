'''
Created on Jul 5, 2010

@author: leifj
'''
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User, Group
import datetime
from django.views.decorators.cache import never_cache
import logging
from apps.room.tasks import import_user_rooms
from apps.room.views import user_meeting_folder
from meetingtools.apps.userprofile.models import UserProfile
from meetingtools.multiresponse import redirect_to, make_response_dict
from meetingtools.ac import ac_api_client
from django.shortcuts import render_to_response
from django.contrib import auth
from django_co_connector.models import co_import_from_request, add_member,remove_member
from meetingtools.apps.cluster.models import acc_for_user
from django.conf import settings

def meta(request,attr):
    v = request.META.get(attr)
    if not v:
        return None
    values = filter(lambda x: x != "(null)",v.split(";"))
    return values;

def meta1(request,attr):
    v = meta(request,attr)
    if v:
        return str(v[0]).decode('utf-8')
    else:
        return None

def _localpart(a):
    if hasattr(a,'name'):
        a = a.name
    if '@' in a:
        (lp,dp) = a.split('@')
        a = lp
    return a

def _is_member_or_employee_old(affiliations):
    lpa = map(_localpart,affiliations)
    return 'student' in lpa or 'staff' in lpa or ('member' in lpa and not 'student' in lpa)

def _is_member_or_employee(user):
    lpa = map(_localpart,user.groups.all())
    return 'student' in lpa or 'staff' in lpa or ('member' in lpa and not 'student' in lpa)

@never_cache
def logout(request):
    auth.logout(request)
    post_logout= "/"
    if hasattr(settings,'POST_LOGOUT'):
        post_logout = settings.POST_LOGOUT

    return HttpResponseRedirect(post_logout)

@never_cache
def login(request):
    return render_to_response('apps/auth/login.html',make_response_dict(request,{'next': request.REQUEST.get("next")}));

def join_group(group,**kwargs):
    user = kwargs['user']
    acc = acc_for_user(user)
    with ac_api_client(acc) as api:    
        principal = api.find_principal("login", user.username, "user")
        if principal:
            gp = api.find_group(group.name)
            if gp:
                api.add_member(principal.get('principal-id'),gp.get('principal-id'))
    
def leave_group(group,**kwargs):
    user = kwargs['user']
    acc = acc_for_user(user)
    with ac_api_client(acc) as api:
        principal = api.find_principal("login", user.username, "user")
        if principal:
            gp = api.find_group(group.name)
            if gp:
                api.remove_member(principal.get('principal-id'),gp.get('principal-id'))

add_member.connect(join_group,sender=Group)
remove_member.connect(leave_group,sender=Group)


def accounts_login_federated(request):
    if request.user.is_authenticated():
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if created:
            profile.identifier = request.user.username
            profile.user = request.user
            profile.save()        
        
        update = False
        fn = meta1(request,'givenName')
        ln = meta1(request,'sn')
        cn = meta1(request,'cn')
        if not cn:
            cn = meta1(request,'displayName')
        logging.debug("cn=%s" % cn)
        if not cn and fn and ln:
            cn = "%s %s" % (fn,ln)
        if not cn:
            cn = profile.identifier
            
        mail = meta1(request,'mail')
        
        idp = meta1(request,'Shib-Identity-Provider')
        
        for attrib_name, meta_value in (('display_name',cn),('email',mail),('idp',idp)):
            attrib_value = getattr(profile, attrib_name)
            if meta_value and not attrib_value:
                setattr(profile,attrib_name,meta_value)
                update = True
                
        if request.user.password == "":
            request.user.password = "(not used for federated logins)"
            update = True
            
        if update:
            request.user.save()
        
        # Allow auto_now to kick in for the lastupdated field
        #profile.lastupdated = datetime.datetime.now()    
        profile.save()

        next = request.session.get("after_login_redirect", None)
        if not next and request.GET.has_key('next'):
            next = request.GET['next']
        else:
            next = settings.DEFAULT_URL

        acc = acc_for_user(request.user)
        with ac_api_client(request) as api:
            # make sure the principal is created before shooting off 
            principal = api.find_or_create_principal("login", request.user.username, "user", 
                                                             {'type': "user",
                                                              'has-children': "0",
                                                              'first-name':fn,
                                                              'last-name':ln,
                                                              'email':mail,
                                                              'send-email': 0,
                                                              'login':request.user.username,
                                                              'ext-login':request.user.username})

            #co_import_from_request(request)
            import_user_rooms(api, request.user)
            
            member_or_employee = _is_member_or_employee(request.user)
            for gn in ('live-admins','seminar-admins'):
                group = api.find_builtin(gn)
                if group:
                    api.add_remove_member(principal.get('principal-id'),group.get('principal-id'),member_or_employee)
            
            #(lp,domain) = uid.split('@')
            #for a in ('student','employee','member'):
            #    affiliation = "%s@%s" % (a,domain)
            #    group = connect_api.find_or_create_principal('name',affiliation,'group',{'type': 'group','has-children':'1','name': affiliation})
            #    member = affiliation in affiliations
            #    connect_api.add_remove_member(principal.get('principal-id'),group.get('principal-id'),member)
                
            #for e in epe:
            #    group = connect_api.find_or_create_principal('name',e,'group',{'type': 'group','has-children':'1','name': e})
            #    if group:
            #        connect_api.add_remove_member(principal.get('principal-id'),group.get('principal-id'),True)

            if next is not None:
                return redirect_to(next)
    else:
        pass

    return redirect_to(settings.LOGIN_URL)
