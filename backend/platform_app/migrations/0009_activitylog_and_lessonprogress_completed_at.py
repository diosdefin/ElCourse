# Generated manually for gamification profile support.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_app', '0008_user_is_verified'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lessonprogress',
            old_name='updated_at',
            new_name='completed_at',
        ),
        migrations.AlterField(
            model_name='lessonprogress',
            name='completed_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('date', models.DateField(auto_now_add=True)),
                (
                    'action_type',
                    models.CharField(
                        choices=[
                            ('lesson_completed', 'Урок завершен'),
                            ('quiz_passed', 'Квиз пройден'),
                        ],
                        max_length=32,
                    ),
                ),
                ('count', models.IntegerField(default=1)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='activity_logs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['date', 'action_type'],
                'unique_together': {('user', 'date', 'action_type')},
            },
        ),
    ]
