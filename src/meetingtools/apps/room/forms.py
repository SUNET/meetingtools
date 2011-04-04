'''
Created on Feb 1, 2011

@author: leifj
'''
from django.forms.models import ModelForm
from meetingtools.apps.room.models import Room
from django.forms.widgets import Select, TextInput
from django.forms.fields import ChoiceField, BooleanField
from django.forms.forms import Form
from form_utils.forms import BetterModelForm
        
PUBLIC = 0
PROTECTED = 1
PRIVATE = 2
        
class UpdateRoomForm(BetterModelForm):
    #protection = ChoiceField(choices=((PUBLIC,'Anyone can enter the room.'),
    #                                  (PROTECTED,'Only group members and accepted guests can enter the room.'),
    #                                  (PRIVATE,'Only group members can enter.')))
    
    class Meta:
        model = Room
        fields = ['name','urlpath','participants','presenters','hosts','source_sco_id','self_cleaning']
        fieldsets = [('name',{'fields': ['name'],
                              'classes': ['step'],
                              'legend': 'Step 1: Room name',
                              'description': 'The room name should be short and descriptive.'
                              }),
                     ('properties',{'fields': ['self_cleaning','urlpath','source_sco_id'],
                                    'classes': ['step'],
                                    'legend': 'Step 2: Room properties',
                                    'description': 'These are basic properties for your room. If you set your room to be self-cleaning it will be reset every time the last participant leaves the room.'}),
                     ('rights',{'fields': ['participants','presenters','hosts'],
                                'classes': ['step','submit_step'],
                                'legend': 'Step 3: Room rights (optional)',
                                'description': 'Define the groups that are to have access to your room.'})               
                    ]
        widgets = {'participants': Select(),
                   'presenters': Select(),
                   'hosts': Select(),
                   'source_sco_id': Select(),
                   'urlpath': TextInput(attrs={'size': '40'}),
                   'name': TextInput(attrs={'size': '40'}),
                   }
        
class DeleteRoomForm(Form):
    confirm = BooleanField(label="Confirm remove room")