# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-31 07:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20170731_0359'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='class',
            name='affects_gwa',
        ),
        migrations.AddField(
            model_name='course',
            name='affects_gwa',
            field=models.BooleanField(default=True),
        ),
    ]