from django.db import migrations, models
from django.utils.text import slugify


def fix_duplicate_product_slugs(apps, schema_editor):
    """Fix duplicate product slugs before adding unique constraint."""
    Product = apps.get_model("seller", "Product")

    # Get all products ordered by id
    products = Product.objects.all().order_by("id")

    seen_slugs = {}
    for product in products:
        base_slug = (
            slugify(product.name) if product.name else slugify(f"product-{product.id}")
        )

        if not base_slug:
            base_slug = f"product-{product.id}"

        if base_slug in seen_slugs:
            # Increment the counter for this slug
            seen_slugs[base_slug] += 1
            product.slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[base_slug] = 1
            product.slug = base_slug

        product.save(update_fields=["slug"])


def reverse_fix(apps, schema_editor):
    """Reverse function - not needed for this migration."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("seller", "0003_sellerprofile_status"),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_product_slugs, reverse_fix),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=255, unique=True, blank=True),
        ),
    ]
