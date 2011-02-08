'''
Created on Feb 1, 2011

@author: leifj
'''
from django.forms.models import ModelForm
from meetingtools.apps.room.models import Room
from django.forms.widgets import Select, TextInput
from django.forms.fields import ChoiceField, BooleanField
from django.forms.forms import Form
        
PUBLIC = 0
PROTECTED = 1
PRIVATE = 2
        
class UpdateRoomForm(ModelForm):
    #protection = ChoiceField(choices=((PUBLIC,'Anyone can enter the room.'),
    #                                  (PROTECTED,'Only group members and accepted guests can enter the room.'),
    #                                  (PRIVATE,'Only group members can enter.')))
    
    class Meta:
        model = Room
        fields = ['name','urlpath','participants','presenters','hosts','source_sco_id','self_cleaning']
        widgets = {'participants': Select(),
                   'presenters': Select(),
                   'hosts': Select(),
                   'source_sco_id': Select(),
                   'urlpath': TextInput(attrs={'size': '40'}),
                   'name': TextInput(attrs={'size': '40'}),
                   }
        
class DeleteRoomForm(Form):
    confirm = BooleanField(label="Confirm remove room")