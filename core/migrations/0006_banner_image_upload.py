from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_alter_otp_otp"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="banners/"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="image_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
