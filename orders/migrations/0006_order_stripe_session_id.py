from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_alter_voucher_order_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stripe_session_id",
            field=models.CharField(
                max_length=255, unique=True, null=True, blank=True
            ),
        ),
    ]
