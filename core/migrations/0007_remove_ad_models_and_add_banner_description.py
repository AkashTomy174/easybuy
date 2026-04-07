from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_banner_image_upload"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.DeleteModel(
            name="AdBooking",
        ),
        migrations.DeleteModel(
            name="AdSpace",
        ),
    ]
