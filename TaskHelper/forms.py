from django import forms
from .models import TaskRecord

class TaskRecordForm(forms.ModelForm):
    class Meta:
        model = TaskRecord
        fields = ['employee', 'date', 'completed', 'errors']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'completed': forms.NumberInput(attrs={'class': 'form-control'}),
            'errors': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'employee': '员工',
            'date': '日期',
            'completed': '完成图片数',
            'errors': '错误图片数',
        }
