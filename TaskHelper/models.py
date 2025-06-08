from django.db import models
from django.utils.translation import gettext_lazy as _


class Employee(models.Model):
    name = models.CharField("员工", max_length=50)
    avatar = models.ImageField("头像", upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = _("员工")              # 单数显示名
        verbose_name_plural = _("员工")       # 复数显示名

    def get_avatar_url(self):
        if self.avatar and self.avatar.name:
            return self.avatar.url
        return '/static/Finder.png'

    def __str__(self):
        return self.name


class TaskRecord(models.Model):
    employee = models.ForeignKey(Employee, verbose_name=_("员工"), on_delete=models.CASCADE)
    date = models.DateField(_("日期"))
    completed = models.PositiveIntegerField(_("完成图片数"), default=0)
    errors = models.PositiveIntegerField(_("错误图片数"), default=0)

    class Meta:
        verbose_name = _("任务记录")
        verbose_name_plural = _("任务记录")
        unique_together = ("employee", "date")

    def __str__(self):
        return f"{self.employee.name} - {self.date}"
