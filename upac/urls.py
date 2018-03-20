"""upac URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

import core.views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', core.views.home, name='home'),
    url(r'^ge$', core.views.ge, name='ge'),
    url(r'^standing$', core.views.standing, name='standing'),
    url(r'^191$', core.views.bypassed_191_rule, name='191'),
    url(r'^experiment$', core.views.experiment, name='experiment'),
    url(r'^not_covered$', core.views.not_covered, name='not_covered'),
    url(r'^musttake191$', core.views.must_take_191, name='must_take_191'),
    url(r'^immortal$', core.views.immortal, name='immortal'),
    url(r'^gwa$', core.views.gwa, name='gwa'),
    url(r'^batch$', core.views.batch, name='batch'),
    url(r'^batchall$', core.views.batch_all, name='batch_all'),
    url(r'^generate$', core.views.generate, name='generate'),
    #url(r'^advising$', core.views.advising, name='advising'),
    #url(r'^single$', core.views.single, name='single'),
]
