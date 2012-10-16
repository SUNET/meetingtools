# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Room'
        db.create_table('room_room', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('sco', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sco.ACObject'], null=True)),
            ('folder_sco', self.gf('django.db.models.fields.related.ForeignKey')(related_name='folders', null=True, to=orm['sco.ACObject'])),
            ('source_sco', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sources', null=True, to=orm['sco.ACObject'])),
            ('deleted_sco', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deleted', null=True, to=orm['sco.ACObject'])),
            ('urlpath', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('self_cleaning', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('allow_host', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('user_count', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('host_count', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('timecreated', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('lastupdated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('lastvisited', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('room', ['Room'])

        # Adding unique constraint on 'Room', fields ['name', 'folder_sco']
        db.create_unique('room_room', ['name', 'folder_sco_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Room', fields ['name', 'folder_sco']
        db.delete_unique('room_room', ['name', 'folder_sco_id'])

        # Deleting model 'Room'
        db.delete_table('room_room')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cluster.accluster': {
            'Meta': {'object_name': 'ACCluster'},
            'api_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'default_template_sco_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'blank': 'True'}),
            'domain_match': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'room.room': {
            'Meta': {'unique_together': "(('name', 'folder_sco'),)", 'object_name': 'Room'},
            'allow_host': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'deleted_sco': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deleted'", 'null': 'True', 'to': "orm['sco.ACObject']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder_sco': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'folders'", 'null': 'True', 'to': "orm['sco.ACObject']"}),
            'host_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastupdated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'lastvisited': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'sco': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sco.ACObject']", 'null': 'True'}),
            'self_cleaning': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'source_sco': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sources'", 'null': 'True', 'to': "orm['sco.ACObject']"}),
            'timecreated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'urlpath': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'user_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'sco.acobject': {
            'Meta': {'unique_together': "(('acc', 'sco_id'),)", 'object_name': 'ACObject'},
            'acc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cluster.ACCluster']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lastupdated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sco_id': ('django.db.models.fields.IntegerField', [], {}),
            'timecreated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['room']