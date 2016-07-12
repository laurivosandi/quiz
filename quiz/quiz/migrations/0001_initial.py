# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-12 10:49
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.TextField()),
                ('correct', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.TextField(help_text='Question itself')),
                ('options', models.IntegerField(default=4, help_text='Maximum number of answer options shown for this question')),
                ('correct', models.IntegerField(default=1, help_text='Minimum number of correct answers shown for this question')),
                ('difficulty', models.IntegerField(choices=[(1, 'easy'), (2, 'average'), (3, 'hard'), (4, 'very hard')], default=2)),
            ],
        ),
        migrations.CreateModel(
            name='Quiz',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('published', models.DateTimeField(blank=True, null=True)),
                ('slug', models.SlugField()),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('tokenized', models.BooleanField(help_text='Whether token is required to access this quiz')),
                ('duration', models.IntegerField(default=60, help_text='Duration for accepting an result for this quiz')),
                ('answers', models.ManyToManyField(blank=True, to='quiz.Answer')),
            ],
            options={
                'verbose_name_plural': 'quizzes',
            },
        ),
        migrations.CreateModel(
            name='QuizToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('valid', models.DateTimeField(blank=True, help_text='When this token can be claimed, immideately if not set', null=True)),
                ('expires', models.DateTimeField(blank=True, help_text='When this token can not be claimed anymore, never if not set', null=True)),
                ('used', models.DateTimeField(blank=True, editable=False, help_text='When this token was used to display the quiz', null=True)),
                ('submitted', models.DateTimeField(blank=True, editable=False, help_text='When this token was used to submit responses for a quiz', null=True)),
                ('invalidated', models.DateTimeField(blank=True, editable=False, null=True)),
                ('reusable', models.BooleanField()),
                ('ip', models.GenericIPAddressField(help_text='IP address which was used to claim this token, prefill to whitelist certain IP', null=True, verbose_name='IP')),
                ('user_agent', models.CharField(editable=False, help_text='User agent that was used to claim this token', max_length=200, null=True)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='quiz.Quiz')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('address', models.GenericIPAddressField()),
                ('user_agent', models.CharField(editable=False, max_length=200, null=True)),
                ('examinee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to=settings.AUTH_USER_MODEL)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='quiz.Quiz')),
            ],
        ),
        migrations.CreateModel(
            name='SubmissionAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('ticked', models.BooleanField()),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='quiz.Answer')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted_answers', to='quiz.Submission')),
            ],
        ),
        migrations.AddField(
            model_name='answer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='quiz.Question'),
        ),
    ]