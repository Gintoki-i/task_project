# 导入依赖
import csv
from collections import defaultdict

from django.http import HttpResponse, JsonResponse
from django.utils.timezone import now
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Sum
from datetime import date, timedelta
from .models import Employee, TaskRecord
import json
from django.utils.safestring import mark_safe


# 首页：轮播图 + 今日图表 + 总进度
def dashboard(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    week = int(request.GET.get('week', today.isocalendar()[1]))

    # 自动计算该年该月的第 N 周对应起始日期
    start_of_week = date.fromisocalendar(year, week, 1)
    end_of_week = start_of_week + timedelta(days=6)

    # 🎯 排行榜数据
    top3 = TaskRecord.objects.filter(date__range=(start_of_week, end_of_week)) \
        .values('employee__id', 'employee__name') \
        .annotate(total_completed=Sum('completed'), total_errors=Sum('errors')) \
        .order_by('-total_completed')[:3]

    for item in top3:
        emp = Employee.objects.get(id=item['employee__id'])
        item['avatar_url'] = emp.get_avatar_url()

    # 今日任务图（仍默认今日）
    today_records = TaskRecord.objects.filter(date=today)
    labels = [r.employee.name for r in today_records]
    completed_data = [r.completed for r in today_records]
    error_data = [r.errors for r in today_records]

    total_completed = sum(completed_data)
    total_target = len(labels) * 160
    progress_percent = round((total_completed / total_target) * 100 if total_target else 0)

    return render(request, 'TaskHelper/dashboard.html', {
        'year': year,
        'month': month,
        'week': week,
        'start_week': start_of_week,
        'end_week': end_of_week,
        'top3_week': top3,
        'labels': labels,
        'completed_data': completed_data,
        'error_data': error_data,
        'progress_percent': progress_percent,
    })

# def dashboard(request):
#     today = now().date()
#     start_week = today - timedelta(days=today.weekday())
#     past_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
#
#     # Top3 员工
#     top3 = TaskRecord.objects.filter(date__range=(start_week, today)) \
#                .values('employee__id', 'employee__name') \
#                .annotate(total_completed=Sum('completed'), total_errors=Sum('errors')) \
#                .order_by('-total_completed')[:3]
#
#     for item in top3:
#         emp = Employee.objects.get(id=item['employee__id'])
#         item['avatar_url'] = emp.get_avatar_url()
#
#     # 今日数据
#     today_records = TaskRecord.objects.filter(date=today)
#     labels = [r.employee.name for r in today_records]
#     completed_data = [r.completed for r in today_records]
#     error_data = [r.errors for r in today_records]
#
#     total_completed = sum(completed_data)
#     total_target = len(labels) * 240
#     progress_percent = round((total_completed / total_target) * 100 if total_target else 0)
#
#     # 最近 7 天趋势（每天总完成数）
#     trend_labels = [d.strftime('%m-%d') for d in past_7_days]
#     trend_data = []
#     for d in past_7_days:
#         total = TaskRecord.objects.filter(date=d).aggregate(sum=Sum('completed'))['sum'] or 0
#         trend_data.append(total)
#
#     # 员工活跃度评分（总完成数越高越活跃）
#     active_scores = TaskRecord.objects.filter(date=today) \
#         .values('employee__name') \
#         .annotate(score=Sum('completed')) \
#         .order_by('-score')
#
#     return render(request, 'TaskHelper/dashboard.html', {
#         'top3_week': top3,
#         'labels': labels,
#         'completed_data': completed_data,
#         'error_data': error_data,
#         'progress_percent': progress_percent,
#         'trend_labels': trend_labels,
#         'trend_data': trend_data,
#         'active_scores': active_scores,
#     })


def task_report(request):
    records = TaskRecord.objects.select_related('employee').order_by('-date', 'employee__name')

    # ✅ 构造 grouped（key: str 日期 → value: [记录列表]）
    grouped = {}
    summary = {}

    for r in records:
        day_str = r.date.strftime('%Y-%m-%d')
        grouped.setdefault(day_str, []).append(r)

    for day, recs in grouped.items():
        summary[day] = {
            'target': len(recs) * 40,
            'completed': sum(r.completed for r in recs),
            'errors': sum(r.errors for r in recs)
        }

    total_target = sum(v['target'] for v in summary.values())
    total_completed = sum(v['completed'] for v in summary.values())
    total_errors = sum(v['errors'] for v in summary.values())

    detail_rows = records

    if request.GET.get('export') == 'csv':
        return export_task_csv(records)

    return render(request, 'TaskHelper/task_report.html', {
        'grouped': grouped,
        'summary': summary,
        'total_target': total_target,
        'total_completed': total_completed,
        'total_errors': total_errors,
        'detail_rows': detail_rows,
    })


def export_task_csv(records):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="任务记录.csv"'
    writer = csv.writer(response)
    writer.writerow(['姓名', '日期', '完成数', '错误数'])
    for r in records:
        writer.writerow([r.employee.name, r.date, r.completed, r.errors])
    return response


# 数据录入页面（批量填写完成数和错误数）
def input_task(request):
    employees = Employee.objects.all().order_by('id')
    today = now().date()
    selected_date = today

    # 所有已录入的日期
    task_dates = TaskRecord.objects.values_list('date', flat=True).distinct()
    highlighted_dates = list(sorted(set(str(d) for d in task_dates)))

    if request.method == 'POST':
        selected_date_str = request.POST.get('record_date') or today.strftime('%Y-%m-%d')
        selected_date = date.fromisoformat(selected_date_str)

        errors = 0
        for emp in employees:
            completed = request.POST.get(f'completed_{emp.id}')
            errors_count = request.POST.get(f'errors_{emp.id}')
            if completed and errors_count:
                try:
                    completed = int(completed)
                    errors_count = int(errors_count)
                    if completed >= 0 and 0 <= errors_count <= completed:
                        TaskRecord.objects.update_or_create(
                            employee=emp,
                            date=selected_date,
                            defaults={'completed': completed, 'errors': errors_count}
                        )
                    else:
                        errors += 1
                except ValueError:
                    errors += 1

        if errors == 0:
            messages.success(request, f"{selected_date} 数据保存成功！")
        else:
            messages.warning(request, f"{selected_date} 部分数据无效（{errors} 项）")

        # 重新获取高亮日期
        task_dates = TaskRecord.objects.values_list('date', flat=True).distinct()
        highlighted_dates = list(sorted(set(str(d) for d in task_dates)))

    return render(request, 'TaskHelper/input_task.html', {
        'employees': employees,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'highlighted_dates': json.dumps(highlighted_dates),
    })


# 获取当前周范围
def get_current_week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


# 周统计图表页面（柱状图）
# def weekly_stats(request):
#     start_date, end_date = get_current_week_range()
#
#     records = TaskRecord.objects.filter(date__range=(start_date, end_date))
#     stats = records.values('employee__name').annotate(
#         total_completed=Sum('completed'),
#         total_errors=Sum('errors')
#     )
#
#     labels = [s['employee__name'] for s in stats]
#     completed_data = [s['total_completed'] for s in stats]
#     error_data = [s['total_errors'] for s in stats]
#
#     return render(request, 'TaskHelper/weekly_stats.html', {
#         'start_date': start_date,
#         'end_date': end_date,
#         'labels': labels,
#         'completed_data': completed_data,
#         'error_data': error_data,
#     })


# 获取当前月范围
def get_current_month_range():
    today = date.today()
    start = today.replace(day=1)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return start, end


#  月统计图表页面
# def monthly_stats(request):
#     start_date, end_date = get_current_month_range()
#
#     records = TaskRecord.objects.filter(date__range=(start_date, end_date))
#     stats = records.values('employee__name').annotate(
#         total_completed=Sum('completed'),
#         total_errors=Sum('errors')
#     )
#
#     labels = [s['employee__name'] for s in stats]
#     completed_data = [s['total_completed'] for s in stats]
#     error_data = [s['total_errors'] for s in stats]
#
#     return render(request, 'TaskHelper/monthly_stats.html', {
#         'start_date': start_date,
#         'end_date': end_date,
#         'labels': labels,
#         'completed_data': completed_data,
#         'error_data': error_data,
#     })


#  周排行页面
def weekly_ranking(request):
    start_date, end_date = get_current_week_range()

    ranking = TaskRecord.objects.filter(date__range=(start_date, end_date)) \
        .values('employee__id', 'employee__name') \
        .annotate(total_completed=Sum('completed'), total_errors=Sum('errors')) \
        .order_by('-total_completed')

    for item in ranking:
        emp = Employee.objects.get(id=item['employee__id'])
        item['avatar_url'] = emp.get_avatar_url()
        records = TaskRecord.objects.filter(employee=emp, date__range=(start_date, end_date)).order_by('date')
        item['chart_labels'] = [r.date.strftime("%Y-%m-%d") for r in records]
        item['chart_values'] = [r.completed for r in records]

    return render(request, 'TaskHelper/weekly_ranking.html', {
        'ranking': ranking,
        'start_date': start_date,
        'end_date': end_date,
    })


#  月排行页面
def monthly_ranking(request):
    start_date, end_date = get_current_month_range()

    ranking = TaskRecord.objects.filter(date__range=(start_date, end_date)) \
        .values('employee__id', 'employee__name') \
        .annotate(total_completed=Sum('completed'), total_errors=Sum('errors')) \
        .order_by('-total_completed')

    for item in ranking:
        emp = Employee.objects.get(id=item['employee__id'])
        item['avatar_url'] = emp.get_avatar_url()
        records = TaskRecord.objects.filter(employee=emp, date__range=(start_date, end_date)).order_by('date')
        item['chart_labels'] = [r.date.strftime("%Y-%m-%d") for r in records]
        item['chart_values'] = [r.completed for r in records]

    return render(request, 'TaskHelper/monthly_ranking.html', {
        'ranking': ranking,
        'start_date': start_date,
        'end_date': end_date,
    })


#  处理周范围或月范围日期显示
def format_range_pair(records, fallback):
    if records.exists():
        dates = sorted([records.first().date, records.last().date])
        return [dates[0].strftime('%Y-%m-%d'), dates[1].strftime('%Y-%m-%d')]
    return fallback


#  月热力图数据（[日, 月名, 数量]）
def build_month_day_heatmap_data(records):
    data = []
    for r in records:
        day = r.date.day
        month = f"{r.date.month}月"
        data.append([str(day), month, r.completed])
    return data


#  周热力图数据（[星期几, 第几周, 数量]）
def build_week_day_heatmap_data(records):
    week_data = defaultdict(lambda: {str(i): 0 for i in range(1, 8)})
    week_labels_set = set()

    for r in records:
        week_num = r.date.isocalendar()[1]
        week_label = f"第{week_num}周"
        weekday = str(r.date.weekday() + 1)
        week_data[week_label][weekday] = r.completed
        week_labels_set.add(week_label)

    week_labels = sorted(week_labels_set)
    result = []

    for week_label in week_labels:
        for day in ['1', '2', '3', '4', '5', '6', '7']:
            result.append([day, week_label, week_data[week_label][day]])

    return result, week_labels


#  员工详情页（含表格、周图、月图）
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    records = TaskRecord.objects.filter(employee=employee).order_by('-date')
    week_records = records.filter(date__gte=week_start)
    month_records = records.filter(date__gte=month_start)

    week_range = format_range_pair(week_records, ["2025-01-01", "2025-01-07"])
    month_range = format_range_pair(month_records, ["2025-01-01", "2025-01-31"])

    month_day_heatmap_data = build_month_day_heatmap_data(records)
    week_day_heatmap_data, week_day_labels = build_week_day_heatmap_data(records)

    return render(request, 'TaskHelper/employee_detail.html', {
        'employee': employee,
        'records': records,
        'week_records': week_records,
        'month_records': month_records,
        'week_range': week_range,
        'month_range': month_range,
        'month_day_heatmap_data': mark_safe(json.dumps(month_day_heatmap_data)),
        'week_day_heatmap_data': mark_safe(json.dumps(week_day_heatmap_data)),
        'week_day_labels': mark_safe(json.dumps(week_day_labels)),
    })


@csrf_exempt
def edit_task_inline(request, task_id):
    if request.method == 'POST':
        record = get_object_or_404(TaskRecord, id=task_id)
        data = json.loads(request.body)
        record.completed = int(data.get("completed", record.completed))
        record.errors = int(data.get("errors", record.errors))
        record.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Invalid'}, status=400)


@csrf_exempt
def delete_task(request, task_id):
    if request.method == 'POST':
        record = get_object_or_404(TaskRecord, id=task_id)
        record.delete()
        return JsonResponse({'status': 'deleted'})
    return JsonResponse({'error': 'Invalid'}, status=400)


def batch_update_tasks(request):
    if request.method == 'POST':
        ids = request.POST.getlist('task_ids')
        for task_id in ids:
            record = get_object_or_404(TaskRecord, id=task_id)
            record.completed = int(request.POST.get(f'completed_{task_id}', record.completed))
            record.errors = int(request.POST.get(f'errors_{task_id}', record.errors))
            record.save()
        messages.success(request, f"已批量更新 {len(ids)} 条记录")
    return redirect('task_report')


@csrf_exempt
def delete_task_batch(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get("ids", [])
        TaskRecord.objects.filter(id__in=ids).delete()
        return JsonResponse({'deleted': len(ids)})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def weekly_stats(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    week = int(request.GET.get('week', today.isocalendar()[1]))

    # 计算当周起止
    start_date = date.fromisocalendar(year, week, 1)
    end_date = start_date + timedelta(days=6)

    records = TaskRecord.objects.filter(date__range=(start_date, end_date))
    stats = records.values('employee__name').annotate(
        total_completed=Sum('completed'),
        total_errors=Sum('errors')
    )

    labels = [s['employee__name'] for s in stats]
    completed_data = [s['total_completed'] for s in stats]
    error_data = [s['total_errors'] for s in stats]

    return render(request, 'TaskHelper/weekly_stats.html', {
        'start_date': start_date,
        'end_date': end_date,
        'labels': labels,
        'completed_data': completed_data,
        'error_data': error_data,
        'year': year,
        'week': week,
    })


def monthly_stats(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    start_date = date(year, month, 1)
    # 获取本月最后一天
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = (next_month.replace(day=1) - timedelta(days=1))

    records = TaskRecord.objects.filter(date__range=(start_date, end_date))
    stats = records.values('employee__name').annotate(
        total_completed=Sum('completed'),
        total_errors=Sum('errors')
    )

    labels = [s['employee__name'] for s in stats]
    completed_data = [s['total_completed'] for s in stats]
    error_data = [s['total_errors'] for s in stats]

    return render(request, 'TaskHelper/monthly_stats.html', {
        'start_date': start_date,
        'end_date': end_date,
        'labels': labels,
        'completed_data': completed_data,
        'error_data': error_data,
        'year': year,
        'month': month,
    })
