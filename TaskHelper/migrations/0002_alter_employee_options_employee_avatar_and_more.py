# Generated by Django 5.2.2 on 2025-06-07 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("TaskHelper", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="employee",
            options={"verbose_name": "姓名", "verbose_name_plural": "姓名"},
        ),
        migrations.AddField(
            model_name="employee",
            name="avatar",
            field=models.ImageField(
                blank=True, null=True, upload_to="avatars/", verbose_name="头像"
            ),
        ),
        migrations.AlterField(
            model_name="employee",
            name="name",
            field=models.CharField(max_length=50, verbose_name="姓名"),
        ),
    ]
