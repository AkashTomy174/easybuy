from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', None)
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")
    
    def _format_phone(self, phone):
        phone = str(phone).strip()
        phone = ''.join(filter(str.isdigit, phone))
        
        if not phone.startswith('91') and len(phone) == 10:
            phone = '91' + phone
        
        return f'whatsapp:+{phone}'
    
    def send_message(self, to_phone, message):
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            to_whatsapp = self._format_phone(to_phone)
            
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=to_whatsapp
            )
            
            logger.info(f"WhatsApp message sent: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return False
    
    def send_order_confirmation(self, order):
        message = f"""
*EasyBuy - Order Confirmation*

🎉 Hi {order.shipping_name},

Your order has been confirmed!

📦 *Order Details:*
Order Number: {order.order_number}
Total Amount: ₹{order.total_amount}
Status: {order.order_status}

📍 *Delivery Address:*
{order.shipping_address}

Thank you for shopping with EasyBuy! 🛍️

Track: http://easybuy.com/user/orders/

---
*EasyBuy E-Commerce*
Your trusted shopping partner
        """.strip()
        
        return self.send_message(order.shipping_phone, message)
    
    def send_order_shipped(self, order):
        message = f"""
*EasyBuy - Order Shipped*

🚚 Hi {order.shipping_name},

Great news! Your order is on its way!

📦 Order Number: {order.order_number}
💰 Amount: ₹{order.total_amount}

Your package will be delivered soon. 📦

Track: http://easybuy.com/user/orders/

---
*EasyBuy E-Commerce*
        """.strip()
        
        return self.send_message(order.shipping_phone, message)
    
    def send_order_delivered(self, order):
        message = f"""
*EasyBuy - Order Delivered*

✅ Hi {order.shipping_name},

Your order has been delivered successfully! 🎉

📦 Order Number: {order.order_number}
💰 Amount: ₹{order.total_amount}

We hope you love your purchase! ❤️

Review: http://easybuy.com/user/orders/

---
*EasyBuy E-Commerce*
Thank you for choosing us!
        """.strip()
        
        return self.send_message(order.shipping_phone, message)
    
    def send_feedback_request(self, order):
        message = f"""
*EasyBuy - We'd Love Your Feedback!*

⭐ Hi {order.shipping_name},

Thank you for your recent purchase!
Order: {order.order_number}

We hope you're enjoying your products. 😊

Please share your experience:
👉 http://easybuy.com/user/orders/

Your feedback helps us serve you better! 🙏

---
*EasyBuy E-Commerce*
        """.strip()
        
        return self.send_message(order.shipping_phone, message)
    
    def send_order_cancelled(self, order):
        message = f"""
*EasyBuy - Order Cancelled*

❌ Hi {order.shipping_name},

Your order has been cancelled.

📦 Order Number: {order.order_number}
💰 Amount: ₹{order.total_amount}

If you have any questions, please contact our support.

We hope to serve you again soon! 🙏

---
*EasyBuy E-Commerce*
        """.strip()
        
        return self.send_message(order.shipping_phone, message)


whatsapp_notifier = WhatsAppNotifier()
