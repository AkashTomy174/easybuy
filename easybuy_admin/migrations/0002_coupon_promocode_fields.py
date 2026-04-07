from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_remove_ad_models_and_add_banner_description"),
        ("seller", "0001_initial"),
        ("easybuy_admin", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="coupon",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promo_codes",
                to="core.category",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="coupon",
            name="discount_type",
            field=models.CharField(
                choices=[("PERCENT", "Percentage"), ("FLAT", "Flat")],
                default="PERCENT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="coupon",
            name="min_order_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="coupon",
            name="name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="coupon",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promo_codes",
                to="seller.product",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="seller",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promo_codes",
                to="seller.sellerprofile",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="subcategory",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promo_codes",
                to="core.subcategory",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
