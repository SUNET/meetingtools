# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ACCluster.cross_domain_sso'
        db.add_column('cluster_accluster', 'cross_domain_sso',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ACCluster.cross_domain_sso'
        db.delete_column('cluster_accluster', 'cross_domain_sso')


    models = {
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
        }
    }

    complete_apps = ['cluster']