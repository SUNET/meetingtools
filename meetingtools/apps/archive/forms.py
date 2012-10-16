from django.forms import Form, CharField

__author__ = 'leifj'

class TagArchiveForm(Form):
    tag = CharField(max_length=256)