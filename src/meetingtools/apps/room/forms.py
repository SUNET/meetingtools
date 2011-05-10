'''
Created on Feb 1, 2011

@author: leifj
'''

from meetingtools.apps.room.models import Room
from django.forms.widgets import Select, TextInput, RadioSelect
from django.forms.fields import BooleanField, ChoiceField, CharField
from django.forms.forms import Form
from form_utils.forms import BetterModelForm
from django.utils.safestring import mark_safe
        
PUBLIC = 0
PROTECTED = 1
PRIVATE = 2
        
class PrefixTextInput(TextInput):
    def __init__(self, attrs=None, prefix=None):
        super(PrefixTextInput, self).__init__(attrs)
        self.prefix = prefix

    def render(self, name, value, attrs=None):
        return mark_safe("<b>"+self.prefix+"</b>&nbsp;"+super(PrefixTextInput, self).render(name, value, attrs))
        
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
                                    'description': '''
                                    These are basic properties for your room. If you set your room to be cleaned up after use it will 
                                    be reset every time the last participant leaves the room.'''
                                    }),
                    ]
        widgets = {'source_sco_id': Select(),
                   'urlpath': PrefixTextInput(attrs={'size': '15'}),
                   'name': TextInput(attrs={'size': '40'})}
        
        
class CreateRoomForm(BetterModelForm):

    access = ChoiceField(choices=(('public','Public'),('private','Private')))
    
    class Meta:
        model = Room
        fields = ['name','urlpath','access','self_cleaning']
        fieldsets = [('name',{'fields': ['name'],
                              'classes': ['step'],
                              'legend': 'Step 1: Room name',
                              'description': 'The room name should be short and descriptive.'
                              }),
                     ('properties',{'fields': ['self_cleaning','urlpath','access'],
                                    'classes': ['step'],
                                    'legend': 'Step 2: Room properties',
                                    'description': '''
                                    <p>These are basic properties for your room. If you set your room to cleaned up after 
                                    use it will be reset every time the last participant leaves the room. If you create a public room it 
                                    will be open to anyone who has the room URL. If you create a private room then guests will have to be 
                                    approved by an active meeting host before being able to join the room.</p>
                                    
                                    <div class="ui-widget">
                                        <div class="ui-state-highlight ui-corner-all" style="margin-top: 20px; padding: 0 .7em;"> 
                                            <p><span class="ui-icon ui-icon-info" style="float: left; margin-right: .3em;"></span>
                                            <strong>Warning</strong> Setting a room to be cleaned up when empty will cause all existing content 
                                            associated with the to be destroyed each time the room is reset.</p>
                                        </div>
                                    </div>
                                    '''
                                    }),               
                    ]
        widgets = {'access': RadioSelect(),
                   'urlpath': PrefixTextInput(attrs={'size': '15'}),
                   'name': TextInput(attrs={'size': '40'})}
        
class DeleteRoomForm(Form):
    confirm = BooleanField(label="Confirm remove room")
    
class TagRoomForm(Form):
    tag = CharField(max_length=256)