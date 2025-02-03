import os
import requests
from flask import Flask, request, jsonify

# =============================================
#           CONFIGURE ENVIRONMENT VARIABLES
# =============================================
INTERAKT_API_KEY = os.getenv("INTERAKT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 5000))  # Default to 5000 if not set
# =============================================

app = Flask(__name__)

def get_product_catalog():
    """Fetch product catalog from Interakt (Standard or Facebook-linked catalog)"""
    try:
        response = requests.get(
            "https://api.interakt.ai/v1/public/facebook/catalogs",  # ✅ Updated API for Facebook catalog
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            }
        )

        print(f"\n📡 Interakt API Response: {response.status_code} - {response.text}")  # ✅ Debugging response

        if response.status_code == 200:
            catalog_items = response.json().get("data", [])
            if not catalog_items:
                return "Sorry, no products are available at the moment."

            product_list = "🛒 *Our Facebook Catalog Products:*\n"
            for item in catalog_items:
                product_list += f"\n🔹 *{item.get('title', 'Unknown Product')}* - {item.get('price', 'N/A')} {item.get('currency', '')}\n{item.get('description', '')}\n"

            product_list += "\nReply with *'Order [Product Name] [Quantity]'* to place an order."
            return product_list
        else:
            return f"⚠️ Unable to fetch products. API Error: {response.status_code}"
    except Exception as e:
        print(f"🔥 Catalog Fetch Error: {str(e)}")
        return "⚠️ Error retrieving product catalog."

def get_ai_response(prompt):
    """Get response from OpenAI with memory for better conversation handling."""
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are the customer support assistant for Sundarban JFMC (sundarbanjfmc.org), "
                                   "a company that sells pure honey and ghee. You must: "
                                   "1️⃣ Answer customer inquiries about honey, ghee, benefits, and orders. "
                                   "2️⃣ Help customers place orders, track orders, and provide delivery details. "
                                   "3️⃣ ONLY discuss Sundarban JFMC topics. If a question is unrelated, respond with: "
                                   "'I'm here to assist with Sundarban JFMC inquiries only.'"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenAI Error: {str(e)}")
        return "We're experiencing technical difficulties. Please try again later."

@app.route('/webhook', methods=['POST'])
def handle_interakt_webhook():
    """Handle incoming messages from Interakt"""
    try:
        data = request.get_json()
        print("\n📥 Incoming Webhook JSON (Raw):\n", json.dumps(data, indent=4))

        if data.get("type") != "message_received":
            print("⚠️ Ignoring non-message events...")
            return jsonify({"status": "ignored", "message": "Non-message event ignored"}), 200

        customer_data = data.get("data", {}).get("customer", {})
        phone_number = customer_data.get("country_code", "") + customer_data.get("phone_number", "")
        message_data = data.get("data", {}).get("message", {})
        message_text = message_data.get("message").strip().lower()

        print(f"📩 Received Message: {message_text} from {phone_number}")

        if "product" in message_text or "catalog" in message_text or "list" in message_text:
            ai_response = get_product_catalog()
        elif message_text.startswith("order "):
            order_details = message_text.split(" ")
            if len(order_details) >= 3:
                product_name = order_details[1]
                quantity = order_details[2]
                ai_response = process_payment(phone_number, product_name, quantity)
            else:
                ai_response = "⚠️ Invalid format. Please use: *Order [Product Name] [Quantity]*"
        elif message_text == "paid":
            ai_response = (
                "✅ Payment received! Your order is confirmed and will be processed shortly.\n"
                "Thank you for shopping with Sundarban JFMC! 🐝🍯"
            )
        else:
            ai_response = get_ai_response(message_text)

        print(f"🤖 AI Response: {ai_response}")

        response = requests.post(
            "https://api.interakt.ai/v1/public/message/",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "fullPhoneNumber": phone_number,
                "type": "Text",
                "data": {"message": ai_response}
            }
        )

        print(f"📡 Interakt Response: {response.status_code} - {response.text}")

        return jsonify({"status": "success", "message": "Message sent"}), 200

    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


def process_payment(phone_number, product_name, quantity):
    """Generate a Razorpay payment link and send it to the customer"""
    try:
        amount = 50000  # Replace with actual product price (in paise, ₹500 = 50000)
        payload = {
            "amount": amount,
            "currency": "INR",
            "accept_partial": False,
            "first_min_partial_amount": amount,
            "description": f"Order for {product_name} (x{quantity})",
            "customer": {"contact": phone_number},
            "notify": {"sms": False, "email": False, "whatsapp": True},
            "callback_url": "https://sundarbanjfmc.org/payment-success",
            "callback_method": "get"
        }

        auth = (os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        response = requests.post("https://api.razorpay.com/v1/payment_links", auth=auth, json=payload)

        if response.status_code == 200:
            payment_data = response.json()
            payment_link = payment_data["short_url"]
            return (
                f"🛒 *Order Summary:*\n"
                f"📦 Product: {product_name}\n"
                f"🔢 Quantity: {quantity}\n"
                f"💰 Total Price: ₹{amount/100}\n"
                f"✅ Complete your payment here: {payment_link}\n"
                f"Once you've completed the payment, reply *'Paid'* to confirm."
            )
        else:
            return f"⚠️ Payment processing failed. Error: {response.text}"
    except Exception as e:
        print(f"🔥 Razorpay Payment Error: {str(e)}")
        return "⚠️ Error processing payment."

@app.route('/webhook/razorpay', methods=['POST'])
def razorpay_webhook():
    """Handle Razorpay Webhook for Payment Confirmation"""
    try:
        data = request.get_json()
        print(f"\n📥 Razorpay Webhook Received:\n{data}")

        event_type = data.get("event")
        if event_type == "payment_link.paid":
            payment_info = data.get("payload", {}).get("payment_link", {}).get("entity", {})
            phone_number = payment_info.get("customer", {}).get("contact", "")
            amount_paid = payment_info.get("amount_paid", 0) / 100
            order_id = payment_info.get("id")

            ai_response = (
                f"✅ Payment of ₹{amount_paid} received!\n"
                f"Your order (ID: {order_id}) is confirmed and will be processed shortly.\n"
                f"Thank you for shopping with Sundarban JFMC! 🐝🍯"
            )

            response = requests.post(
                "https://api.interakt.ai/v1/public/message/",
                headers={
                    "Authorization": f"Basic {INTERAKT_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "fullPhoneNumber": phone_number,
                    "type": "Text",
                    "data": {"message": ai_response}
                }
            )

            print("✅ Payment Confirmation Sent to Customer")
            return jsonify({"status": "success", "message": "Payment confirmed"}), 200
        elif event_type == "payment_link.expired":
            print("⚠️ Payment link expired, no action needed.")
            return jsonify({"status": "ignored", "message": "Payment link expired"}), 200
        else:
            print("⚠️ Unhandled Razorpay Event")
            return jsonify({"status": "ignored", "message": "Unhandled event"}), 400
    except Exception as e:
        print(f"🔥 Razorpay Webhook Error: {str(e)}")
        return jsonify({"status": "error", "message": "Webhook processing failed"}), 500



if __name__ == '__main__':
    import os
    PORT = int(os.getenv("PORT", 10000))  # Default to 10000 if Render assigns it
    print(f"\n🚀 Starting WhatsApp AI Assistant on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)

