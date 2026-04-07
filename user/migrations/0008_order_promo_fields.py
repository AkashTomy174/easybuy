from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0007_order_payment_method_orderitem_stock_deducted"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="promo_code",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
