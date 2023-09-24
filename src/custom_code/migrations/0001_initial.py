# Generated by Django 4.2.4 on 2023-09-22 15:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tom_targets', '0020_alter_targetname_created_alter_targetname_modified'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectTargetList',
            fields=[
                ('targetlist_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tom_targets.targetlist')),
                ('tns', models.BooleanField(help_text='Whether to query TNS catalog')),
                ('sn_type', models.CharField(help_text='The supernova type to check for.', max_length=100)),
            ],
            bases=('tom_targets.targetlist',),
        ),
        migrations.CreateModel(
            name='QuerySet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The query name', max_length=100)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='custom_code.projecttargetlist')),
            ],
        ),
        migrations.CreateModel(
            name='QueryTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('antares_name', models.CharField(help_text='The tag name when queried from ANTARES', max_length=100)),
                ('queryset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='custom_code.queryset')),
            ],
        ),
        migrations.CreateModel(
            name='QueryProperty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('antares_name', models.CharField(help_text='The property name when queried from ANTARES', max_length=100)),
                ('min_value', models.FloatField(help_text='Minimum value', null=True)),
                ('max_value', models.FloatField(help_text='Maximum value', null=True)),
                ('categorical', models.BooleanField(default=False, help_text='Whether property value is categorical (as opposed to continuous)')),
                ('target_value', models.CharField(help_text='Target property value if categorical', max_length=100, null=True)),
                ('queryset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='custom_code.queryset')),
            ],
        ),
        migrations.AddConstraint(
            model_name='querytag',
            constraint=models.UniqueConstraint(fields=('queryset', 'antares_name'), name='no_repeat_query_tags'),
        ),
        migrations.AddConstraint(
            model_name='queryproperty',
            constraint=models.UniqueConstraint(fields=('queryset', 'antares_name'), name='no_repeat_query_properties'),
        ),
    ]
