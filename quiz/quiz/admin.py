from django.db import models
from django.contrib import admin
from django.forms import CheckboxSelectMultiple
from quiz.quiz.models import *

class MyModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {'widget': CheckboxSelectMultiple},
    }


admin.site.register(Quiz, MyModelAdmin)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Submission)
admin.site.register(SubmissionAnswer)
admin.site.register(QuizToken)

