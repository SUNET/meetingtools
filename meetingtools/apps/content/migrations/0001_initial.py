# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Content'
        db.create_table('content_content', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('sco', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sco.ACObject'], unique=True, null=True)),
            ('folder_sco', self.gf('django.db.models.fields.related.ForeignKey')(related_name='content_folders', null=True, to=orm['sco.ACObject'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('urlpath', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('bytecount', self.gf('django.db.models.fields.BigIntegerField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')()),
            ('modified', self.gf('django.db.models.fields.DateTimeField')()),
            ('views', self.gf('django.db.models.fields.IntegerField')()),
            ('lastviewed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('content', ['Content'])


    def backwards(self, orm):
        # Deleting model 'Content'
        db.delete_table('content_content')


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
            'cross_domain_sso': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'default_template_sco_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'blank': 'True'}),
            'domain_match': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'content.content': {
            'Meta': {'object_name': 'Content'},
            'bytecount': ('django.db.models.fields.BigIntegerField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'folder_sco': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_folders'", 'null': 'True', 'to': "orm['sco.ACObject']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastviewed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'sco': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sco.ACObject']", 'unique': 'True', 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'urlpath': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'views': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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

    complete_apps = ['content']