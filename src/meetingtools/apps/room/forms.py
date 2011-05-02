'''
Created on Feb 1, 2011

@author: leifj
'''
from django.forms.models import ModelChoiceField
from meetingtools.apps.room.models import Room
from django.forms.widgets import Select, TextInput
from django.forms.fields import BooleanField
from django.forms.forms import Form
from form_utils.forms import BetterModelForm
from django.contrib.auth.models import Group
        
PUBLIC = 0
PROTECTED = 1
PRIVATE = 2
        
class ModifyRoomForm(BetterModelForm):
    class Meta:
        model = Room
        fields = ['name','source_sco_id','self_cleaning']
        fieldsets = [('name',{'fields': ['name'],
                              'classes': ['step'],
                              'legend': 'Step 1: Room name',
                              'description': 'The room name should be short and descriptive.'
                              }),
                     ('properties',{'fields': ['self_cleaning','urlpath','source_sco_id'],
                                    'classes': ['step'],
                                    'legend': 'Step 2: Room properties',
                                    'description': 'These are basic properties for your room. If you set your room to be self-cleaning it will be reset every time the last participant leaves the room.'}),
                    ]
        widgets = {'source_sco_id': Select(),
                   'urlpath': TextInput(attrs={'size': '40'}),
                   'name': TextInput(attrs={'size': '40'})}
        
        
class CreateRoomForm(BetterModelForm):
    
    participants = ModelChoiceField(Group,required=False)
    presenters = ModelChoiceField(Group,required=False)
    hosts = ModelChoiceField(Group,required=False)
    
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
                                'description': 'Define the groups that are to have access to your room. If you leave the <em>Participants</em> field empty that implies that anyone who knows the URL may enter the room.'})               
                    ]
        widgets = {'source_sco_id': Select(),
                   'urlpath': TextInput(attrs={'size': '40'}),
                   'name': TextInput(attrs={'size': '40'})}
        
class DeleteRoomForm(Form):
    confirm = BooleanField(label="Confirm remove room")