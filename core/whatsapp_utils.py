import logging
from urllib.parse import urljoin

from django.conf import settings
from twilio.rest import Client


logger = logging.getLogger(__name__)


def _public_path_url(path):
    base_url = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    if base_url:
        return urljoin(f"{base_url}/", str(path or "/").lstrip("/"))
    return str(path or "/")


class WhatsAppNotifier:
    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_FROM", None)

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")

    def _format_phone(self, phone):
        phone = str(phone).strip()
        phone = "".join(filter(str.isdigit, phone))

        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        return f"whatsapp:+{phone}"

    def send_message(self, to_phone, message):
        if not self.client:
            logger.error("Twilio client not initialized")
            return False

        try:
            to_whatsapp = self._format_phone(to_phone)
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=to_whatsapp,
            )
            logger.info("WhatsApp message sent: %s", message.sid)
            return True
        except Exception as exc:
            logger.error("Failed to send WhatsApp message: %s", exc)
            return False

    def send_order_confirmation(self, order):
        orders_url = _public_path_url("/user/orders/")
        message = f"""
*EasyBuy - Order Confirmation*

Hi {order.shipping_name},

Your order has been confirmed.

Order Number: {order.order_number}
Total Amount: Rs.{order.total_amount}
Status: {order.order_status}

Delivery Address:
{order.shipping_address}

Track: {orders_url}

EasyBuy E-Commerce
Your trusted shopping partner
        """.strip()

        return self.send_message(order.shipping_phone, message)

    def send_order_shipped(self, order):
        orders_url = _public_path_url("/user/orders/")
        message = f"""
*EasyBuy - Order Shipped*

Hi {order.shipping_name},

Great news. Your order is on its way.

Order Number: {order.order_number}
Amount: Rs.{order.total_amount}

Track: {orders_url}

EasyBuy E-Commerce
        """.strip()

        return self.send_message(order.shipping_phone, message)

    def send_order_delivered(self, order):
        orders_url = _public_path_url("/user/orders/")
        message = f"""
*EasyBuy - Order Delivered*

Hi {order.shipping_name},

Your order has been delivered successfully.

Order Number: {order.order_number}
Amount: Rs.{order.total_amount}

Review: {orders_url}

EasyBuy E-Commerce
Thank you for choosing us
        """.strip()

        return self.send_message(order.shipping_phone, message)

    def send_feedback_request(self, order):
        orders_url = _public_path_url("/user/orders/")
        message = f"""
*EasyBuy - We'd Love Your Feedback*

Hi {order.shipping_name},

Thank you for your recent purchase.
Order: {order.order_number}

Please share your experience:
{orders_url}

Your feedback helps us serve you better.

EasyBuy E-Commerce
        """.strip()

        return self.send_message(order.shipping_phone, message)

    def send_order_cancelled(self, order):
        message = f"""
*EasyBuy - Order Cancelled*

Hi {order.shipping_name},

Your order has been cancelled.

Order Number: {order.order_number}
Amount: Rs.{order.total_amount}

If you have any questions, please contact support.

EasyBuy E-Commerce
        """.strip()

        return self.send_message(order.shipping_phone, message)


whatsapp_notifier = WhatsAppNotifier()
