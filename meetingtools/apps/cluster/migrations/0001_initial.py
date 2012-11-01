# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ACCluster'
        db.create_table('cluster_accluster', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('api_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('user', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128, blank=True)),
            ('default_template_sco_id', self.gf('django.db.models.fields.IntegerField')(unique=True, blank=True)),
            ('domain_match', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('cluster', ['ACCluster'])


    def backwards(self, orm):
        # Deleting model 'ACCluster'
        db.delete_table('cluster_accluster')


    models = {
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
        }
    }

    complete_apps = ['cluster']