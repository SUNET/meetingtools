import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from tagging.models import Tag
from meetingtools.apps.archive.forms import TagArchiveForm
from meetingtools.apps.archive.models import publish_archive, Archive
from meetingtools.apps.room.models import Room
from meetingtools.multiresponse import redirect_to, respond_to

__author__ = 'leifj'

class HttpRedirect(object):
    pass

@login_required
def publish_sco(request,rid,sco_id):
    room = get_object_or_404(Room,pk=rid)
    acc = room.sco.sco_id
    ar = publish_archive(room,sco_id)
    return redirect_to("/room/%d/recordings#%d" % (rid,ar.sco.sco_id))

def _can_tag(request,tag):
    if tag in ('selfcleaning','cleaning','public','private'):
        return False,"'%s' is reserved" % tag
        # XXX implement access model for tags here soon
    return True,""

@never_cache
@login_required
def untag(request,rid,tag):
    ar = get_object_or_404(Archive,pk=rid)
    new_tags = []
    for t in Tag.objects.get_for_object(ar):
        if t.name != tag:
            new_tags.append(t.name)

    Tag.objects.update_tags(ar, ' '.join(new_tags))
    return redirect_to("/archive/%d/tag" % ar.id)

@never_cache
@login_required
def tag(request,rid):
    archive = get_object_or_404(Archive,pk=rid)
    if request.method == 'POST':
        form = TagArchiveForm(request.POST)
        if form.is_valid():
            for tag in re.split('[,\s]+',form.cleaned_data['tag']):
                tag = tag.strip()
                if tag:
                    ok,reason = _can_tag(request,tag)
                    if ok:
                        Tag.objects.add_tag(archive, tag)
                    else:
                        form._errors['tag'] = form.error_class([u'%s ... please choose another tag!' % reason])
    else:
        form = TagArchiveForm()

    tags = Tag.objects.get_for_object(archive)
    tn = "+".join([t.name for t in tags])
    return respond_to(request,
        {'text/html': "apps/archive/tag.html"},
        {'form': form,'formtitle': 'Add Tag','cancelname':'Done','submitname': 'Add Tag','archive': archive, 'tagstring': tn,'tags': tags})
