"""
Created on Jan 16, 2012

@author: leifj
"""
from django.contrib.auth.models import User
from django.forms import ModelChoiceField
from django.forms.forms import Form
from django.forms.fields import DateTimeField, CharField
from meetingtools.apps.sco.models import ACObject

class StatCaledarForm(Form):
    tags = CharField(required=False)
    user = ModelChoiceField(User.objects,required=False)
    sco = ModelChoiceField(ACObject.objects,required=False)
    begin = DateTimeField(required=False)
    end = DateTimeField(required=False)