# quiz
Yet another quiz web application

Install dependencies:

  apt-get install -y python-pip python-dev python-mysql.connector build-essential

Clone repository:

  git clone https://github.com/laurivosandi/quiz /srv/quiz

In /srv/quiz/quiz/local_settings.py:
Override DATABASES to set up MySQL connection.
Set STATIC_ROOT to run collectstatic
Generate random SECRET_KEY

Create uWSGI configuration file /etc/uwsgi/apps-enabled/quiz.ini:

```ini
[uwsgi]
chdir           = /srv/quiz/
module          = quiz.wsgi
master          = true
processes       = 10
vacuum          = true
```
