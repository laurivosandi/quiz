from __future__ import unicode_literals
from datetime import datetime, timedelta
from django.db import models
from django.db.models import Q
from django.contrib import admin
from django.contrib.auth.models import User
from collections import Counter
import uuid


YEAR_IN_SCHOOL_CHOICES = (
    ('FR', 'Freshman'),
    ('SO', 'Sophomore'),
    ('JR', 'Junior'),
    ('SR', 'Senior'),
)

class Question(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    title = models.TextField(
        help_text="Question itself")
    options = models.IntegerField(default=4,
        help_text="Maximum number of answer options shown for this question")
    correct = models.IntegerField(default=1,
        help_text="Minimum number of correct answers shown for this question")

    DIFFICULTIES = (
        (1, "easy"),
        (2, "average"),
        (3, "hard"),
        (4, "very hard"),
    )

    difficulty = models.IntegerField(
        choices=DIFFICULTIES, default=2)

    def __unicode__(self):
        return "%s (%s)" % (self.title, dict(self.DIFFICULTIES)[self.difficulty])


class Answer(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    question = models.ForeignKey(Question, related_name="answers")
    title = models.TextField()
    correct = models.BooleanField()

    @property
    def tag(self):
        return "q%da%d" % (self.question.id, self.id)

    def __unicode__(self):
        return "%s (%s) %s" % (self.title, "correct" if self.correct else "incorrect", self.question)


class Quiz(models.Model):
    class Meta:
        verbose_name_plural = "quizzes"

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    published = models.DateTimeField(null=True, blank=True)

    slug = models.SlugField()
    title = models.CharField(max_length=200)

    description = models.TextField()
    answers = models.ManyToManyField(Answer, blank=True)
    tokenized = models.BooleanField(
        help_text="Whether token is required to access this quiz")
    duration = models.IntegerField(default=60,
        help_text="Duration for accepting an result for this quiz")

    def __unicode__(self):
        return self.title

    def distribution(self):
        counts = Counter()
        lookup = dict(Question.DIFFICULTIES)
        for question in set([j.question for j in self.answers.select_related("question").all()]):
            counts[lookup[question.difficulty]] += 1
        return counts.items()

class QuizTokenManager(models.Manager):
    def valid(self, now=None, used=False):
        if not now:
            now = datetime.now()
        return self.select_related("quiz").filter(
            Q(valid__lt=now) | Q(valid__isnull=True),
            Q(expires__gt=now) | Q(expires__isnull=True),
            used__isnull=not used,
            invalidated__isnull=True)


class QuizToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    valid = models.DateTimeField(null=True, blank=True,
        help_text="When this token can be claimed, immideately if not set")
    expires = models.DateTimeField(null=True, blank=True,
        help_text="When this token can not be claimed anymore, never if not set")
    user = models.ForeignKey(User, related_name="tokens", null=True)
    quiz = models.ForeignKey(Quiz, related_name="tokens")
    used = models.DateTimeField(null=True, blank=True, editable=False,
        help_text="When this token was used to display the quiz")
    submitted = models.DateTimeField(null=True, blank=True, editable=False,
        help_text="When this token was used to submit responses for a quiz")
    invalidated = models.DateTimeField(null=True, blank=True, editable=False)
    reusable = models.BooleanField()
    ip = models.GenericIPAddressField(verbose_name='IP', null=True,
        help_text="IP address which was used to claim this token, prefill to whitelist certain IP")
    user_agent = models.CharField(max_length=200, null=True, editable=False,
        help_text="User agent that was used to claim this token")

    objects = QuizTokenManager()

    def encode(self):
        digits = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ"
        number = self.id.int
        res = ''
        while not res or number > 0:
            number, i = divmod(number, 36)
            res = digits[i] + res
        return res

    def pin(self):
        return "%05d" % int(self.id.hex[:4], 16)

    def __unicode__(self):
        if self.ip:
            return "Token %s for %s to access %s at %s" % (self.id, self.user or "anonymous", self.quiz, self.ip)
        return "Token %s for %s to access %s" % (self.id, self.user or "anonymous", self.quiz)


class Submission(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    quiz = models.ForeignKey(Quiz, related_name="submissions")
    examinee = models.ForeignKey(User, related_name="submissions")
    address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=200, null=True, editable=False)

    def __unicode__(self):
        return "Submission by %s" % (self.examinee,)


class SubmissionAnswer(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    submission = models.ForeignKey(Submission, related_name="submitted_answers")
    answer = models.ForeignKey(Answer, related_name="submissions")
    ticked = models.BooleanField()

    @property
    def correct(self):
        return self.ticked == self.answer.correct

    def __unicode__(self):
        return "Answered %s: %d" % (self.answer, self.ticked)


Answer._meta.ordering=["question"]
User.__unicode__ = lambda u: "%s %s (%s)" % (u.last_name, u.first_name, u.username) if u.first_name and u.last_name else u.username

