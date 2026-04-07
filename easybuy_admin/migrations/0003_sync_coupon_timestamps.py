from django.db import migrations, models
from django.utils import timezone


def backfill_coupon_timestamps(apps, schema_editor):
    Coupon = apps.get_model("easybuy_admin", "Coupon")
    now = timezone.now()
    Coupon.objects.filter(created_at__isnull=True).update(created_at=now)
    Coupon.objects.filter(updated_at__isnull=True).update(updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ("easybuy_admin", "0002_coupon_promocode_fields"),
    ]

    operations = [
        migrations.RunPython(
            backfill_coupon_timestamps, migrations.RunPython.noop
        ),
        migrations.AlterModelOptions(
            name="coupon",
            options={"ordering": ["code"]},
        ),
        migrations.AlterField(
            model_name="coupon",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="coupon",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
