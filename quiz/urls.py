
from django.conf.urls import url
from django.contrib import admin
from quiz import views
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^quiz/([\w-]+)/$', views.QuizView.as_view()),
    url(r'^submission/$', views.submit),
    url(r'^submission/(\d+)/$', views.submission),
    url(r'^unlock/$', views.unlock),
    url(r'^results/$', views.results),
    url(r'^$', views.home),

    url(r'^token/$', staff_member_required(views.TokenGenerator.as_view())),
    url(r'^stats/$', staff_member_required(views.stats)),
    url(r'^stats/(\d+)/$', staff_member_required(views.answer_stats))
]
