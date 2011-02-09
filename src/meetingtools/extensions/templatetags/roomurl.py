from django import template
from meetingtools.settings import BASE_URL
 
register = template.Library()
 
MOMENT = 120    # duration in seconds within which the time difference 
                # will be rendered as 'a moment ago'
 
def roomurl(room):
    """
    Display the public 'go' URL of a meetingroom
    """
    path = room.id
    if room.urlpath:
        path = room.urlpath
    
    return "%s/go/%s" % (BASE_URL,path)
    
roomurl.is_safe = True
register.filter(roomurl)