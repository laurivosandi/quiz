# coding: utf-8
import base64
import ldap
import random
import re
import textwrap
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.views.generic import TemplateView, View
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import render, redirect
from middleware import cert2user
from quiz.quiz.models import Quiz, Question, Answer, Submission, SubmissionAnswer, QuizToken


SQL_RESULTS = """
select
  quiz_submission.id,
  quiz_submission.created as submitted,
  auth_user.first_name as first_name,
  auth_user.last_name as last_name,
  auth_user.username as username,
  sum(
    case
      when quiz_answer.correct and quiz_submissionanswer.ticked
      then quiz_question.difficulty
      else 0
    end
  ) as points,
  quiz_quiz.title as quiz_title,
  quiz_submission.quiz_id as quiz_id,
  auth_user.id as user_id
from
  quiz_submissionanswer
join
  quiz_answer
join
  quiz_question
join
  quiz_submission
join
  quiz_quiz
join
  auth_user
on
  quiz_answer.id = quiz_submissionanswer.answer_id and
  quiz_question.id = quiz_answer.question_id  and
  quiz_submission.id = quiz_submissionanswer.submission_id and
  quiz_quiz.id = quiz_submission.quiz_id  and
  auth_user.id = quiz_submission.examinee_id
where (quiz_submission.id, quiz_question.id) not in (
  select distinct
    quiz_submission.id,
    quiz_question.id
  from
    quiz_submissionanswer
  join
    quiz_submission
  join
    quiz_answer
  join
    quiz_question
  on
    quiz_submission.id = quiz_submissionanswer.submission_id and
    quiz_answer.id = quiz_submissionanswer.answer_id and
    quiz_question.id = quiz_answer.question_id
  where
    not quiz_answer.correct and
    quiz_submissionanswer.ticked
)
group by
  quiz_submission.id
order by
  points desc,
  submitted
"""

SQL_STATS = """
select
  quiz_answer.id,
  quiz_question.title as "question",
  quiz_answer.title as "answer",
  quiz_answer.correct as "tick_expected",
  sum(quiz_answer.correct = quiz_submissionanswer.ticked) as "correct",
  count(*) as "total",
  sum(quiz_answer.correct = quiz_submissionanswer.ticked) * 100 / count(*) as "ratio"
from
  quiz_submissionanswer
join
  quiz_answer
join
  quiz_question
on
  quiz_submissionanswer.answer_id = quiz_answer.id and
  quiz_answer.question_id = quiz_question.id
group by
  quiz_answer.id
order by ratio desc
"""

def stats(req):
    answers = Submission.objects.raw(SQL_STATS)
    return render(req, "stats.html", locals())

def answer_stats(req, answer_id):
    answer = Answer.objects.get(id=answer_id)
    submissions = SubmissionAnswer.objects.select_related("answer", "submission__examinee").filter(answer__id=answer_id).order_by("created")
    return render(req, "answer_stats.html", locals())

def unlock(req):
    try:
        token = QuizToken.objects.valid().get(
            user__username = req.GET.get("username"),
            id__startswith = "%04x" % int(req.GET.get("code")))
    except (QuizToken.DoesNotExist, ValueError):
        messages.error(req, 'Vale või aegunud kood!')
        return redirect("/")
    else:
        return redirect("/quiz/%s/?token=%s" % (token.quiz.slug, token.id))

def results(req):
    submissions = Submission.objects.raw(SQL_RESULTS)
    return render(req, "results.html", locals())


def submission(req, submission_id):
    submission = Submission.objects.get(pk=submission_id)
    submitted_answers = SubmissionAnswer.objects.filter(submission__id=submission_id).select_related("answer")
    total = 0
    correct = {}

    for submitted_answer in submitted_answers:
        if submitted_answer.answer.correct:
            total += submitted_answer.answer.question.difficulty
            if submitted_answer.ticked:
                correct[submitted_answer.answer.question] = correct.get(submitted_answer.answer.question, 0) + submitted_answer.answer.question.difficulty


    for submitted_answer in submitted_answers:
        if not submitted_answer.answer.correct:
            if submitted_answer.ticked:
                correct[submitted_answer.answer.question] = 0

    correct = sum(correct.values())

    # messages add: your submission ID was XXX
    return redirect("/results/")


@transaction.atomic
def submit(req):
    now = timezone.now()
    quiz=Quiz.objects.get(pk=req.POST.get("quiz_id"))

    # The quiz has to be accessible either using a token
    if quiz.tokenized:
        try:
            token = QuizToken.objects.get(
                invalidated__isnull=True,
                id=req.POST.get("token"),
                ip=req.META.get("REMOTE_ADDR"),
                user_agent = req.META.get('HTTP_USER_AGENT'),
                used__isnull=False)
        except QuizToken.DoesNotExist:
            messages.error(req, 'Vale kood!')
            return redirect("/")
        else:
            deadline = token.used + timedelta(minutes=quiz.duration)
            if now > deadline:
                messages.error(req, 'Jäid hiljaks vastuste esitamisega!')
                return redirect("/")
            token.submitted = now
            token.save()
            user = token.user

    # Or if quiz has been published for everyone
    elif quiz.published < now:
        user = req.user
    else:
        messages.error(req, 'Küsimustik avaldamata või pole koodi!')
        return redirect("/")

    submission = Submission.objects.create(
        address=req.META.get("REMOTE_ADDR"),
        user_agent=req.META.get("HTTP_USER_AGENT"),
        quiz=quiz,
        examinee=user)

    for answer in submission.quiz.answers.all().select_related("question"):
        SubmissionAnswer.objects.create(
            submission=submission,
            answer=answer,
            ticked=req.POST.get(answer.tag) in ("1", "on", "checked"))

    messages.error(req, 'Sinu kasutaja identifikaator on %d, selle abil saad enda positsiooni pingereas kontrollida' % user.id)

    return redirect("/submission/%d/" % submission.id)


def home(req):
    """
    View for listing quizzes
    """
    user = req.user
    now = timezone.now()

    if req.user.is_staff:
        quizzes = Quiz.objects.all()
    else:
        quizzes = Quiz.objects.filter(published__gt=now)

        if req.user.is_authenticated():
            tokens = QuizToken.objects.valid().filter(
                used__isnull=True,
                user=req.user)

    return render(req, "index.html", locals())


class QuizView(TemplateView):
    def get(self, req, quiz_slug):
        """
        View for displaying the quiz questions
        """
        now = timezone.now()
        quiz = Quiz.objects.get(slug=quiz_slug)
        if not req.user.is_staff:
            if quiz.tokenized:
                try:
                    token = QuizToken.objects.valid(now).get(id=req.GET.get("token"))
                except QuizToken.DoesNotExist:
                    messages.error(req, 'Vale kood või kood juba kasutatud!')
                    return redirect("/")
                else:
                    if token.ip:
                        if token.ip != req.META.get("REMOTE_ADDR"):
                            messages.error(req, 'Küsimustik pole saadaval sinu asukohas!')
                            return redirect("/")
                    else:
                        token.ip = req.META.get("REMOTE_ADDR")
                    token.used = now
                    token.user_agent = req.META.get('HTTP_USER_AGENT')
                    token.save()
                    deadline = token.used + timedelta(minutes=quiz.duration)

        if quiz.published:
            remaining = quiz.published - now

        q = {}
        points = 0
        from collections import Counter
        distribution = Counter()
        for answer in quiz.answers.all():
            points += answer.question.difficulty if answer.correct else 0
            q[answer.question] = q.get(answer.question, []) + [answer]
            random.shuffle(q[answer.question])
        for question, answers in q.items():
            distribution[question.difficulty] += 1
            if not sum([answer.correct for answer in answers]):
                raise ValueError("No correct answers for: %s" % question)

        questions = sorted(q.items(), key=lambda j:j[0].difficulty)
        return render(req, "quiz.html", locals())


class TokenGenerator(TemplateView):
    template_name = "token.html"

    def get(self, req):
        """
        List generated tokens and show the form for generating new ones
        """
        now = timezone.now()
        tokens = QuizToken.objects.select_related("user", "quiz").all().order_by("user__last_name", "user__first_name", "-created")
        return render(req, "token.html", locals())

    def post(self, req):
        """
        Handle token generation
        """

        # Attempt to fetch first name, last name and e-mail by national identification number
        ft = "serialNumber=%d" % int(req.POST.get("identifier"))
        now = timezone.now()
        conn = ldap.initialize("ldap://ldap.sk.ee")
        attribs = "serialNumber", "userCertificate;binary"
        args = "ou=Authentication,o=ESTEID,c=EE", ldap.SCOPE_SUBTREE, ft, attribs
        for dn, attributes in conn.search_s(*args):
            pem = ["-----BEGIN CERTIFICATE-----"]
            for line in textwrap.wrap(base64.b64encode(attributes["userCertificate;binary"].pop()), 64):
                pem.append(line)
            pem.append("-----END CERTIFICATE-----")
            user = cert2user("\n".join(pem))
            break
        else:
            user = User.objects.create(username=req.POST.get("identifier"))
        conn.unbind_s()

        # Invalidate any already existing tokens
        QuizToken.objects.filter(user = user).update(invalidated=now)

        # Create new token
        token = QuizToken.objects.create(
            user = user,
            valid = now - timedelta(minutes=15),
            expires = now + timedelta(minutes=90),
            quiz = Quiz.objects.order_by('?').first(),
            reusable = False)
        return redirect("/token/#user_%d" % token.user.id)
