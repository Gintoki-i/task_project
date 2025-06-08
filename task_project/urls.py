"""
URL configuration for task_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
python manage.py startapp TaskHelper

"""

from django.contrib import admin
from django.urls import path
from TaskHelper import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path("admin/", admin.site.urls),
    path('input/', views.input_task, name='input_task'),
    path('weekly/', views.weekly_stats, name='weekly_stats'),
    path('monthly/', views.monthly_stats, name='monthly_stats'),
    path('ranking/week/', views.weekly_ranking, name='weekly_ranking'),
    path('ranking/month/', views.monthly_ranking, name='monthly_ranking'),
    path('employee/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employee/task_report/', views.task_report, name='task_report'),

    path('task/<int:task_id>/edit-inline/', views.edit_task_inline, name='edit_task_inline'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('task/batch-update/', views.batch_update_tasks, name='batch_update_tasks'),
    path('task/delete-batch/', views.delete_task_batch, name='delete_task_batch'),




] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

