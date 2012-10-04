'''
Created on Jan 16, 2012

@author: leifj
'''
from django.forms.forms import Form
from django.forms.fields import DateTimeField

class StatCaledarForm(Form):
    begin = DateTimeField(required=False)
    end = DateTimeField(required=False)