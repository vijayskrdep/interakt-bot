import os
import requests
from flask import Flask, request, jsonify

# =============================================
#           CONFIGURE ENVIRONMENT VARIABLES
# =============================================
INTERAKT_API_KEY = os.getenv("INTERAKT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))  # Default to 10000 if Render assigns it
# =============================================

app = Flask(__name__)

def get_product_catalog():
    """Fetch product catalog from Interakt"""
    try:
        response = requests.get(
            "https://api.interakt.ai/v1/public/facebook/catalogs",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            }
        )

        print(f"\n📡 Interakt API Response: {response.status_code} - {response.text}")

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
    """Get AI-generated response with contextual memory"""
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
        import json
        print("\n📥 Incoming Webhook JSON (Raw):\n", json.dumps(data, indent=4))

        if not data or "type" not in data or "data" not in data:
            return jsonify({"status": "error", "message": "Invalid JSON format"}), 400

        if data.get("type") != "message_received":
            return jsonify({"status": "ignored", "message": "Non-message event ignored"}), 200

        customer_data = data.get("data", {}).get("customer", {})
        phone_number = customer_data.get("country_code", "") + customer_data.get("phone_number", "")
        message_data = data.get("data", {}).get("message", {})
        message_text = message_data.get("message", "").strip().lower()

        print(f"📩 Received Message: {message_text} from {phone_number}")

        if not phone_number or not message_text:
            return jsonify({"status": "error", "message": "Missing phone number or message"}), 400

        if "product" in message_text or "catalog" in message_text or "list" in message_text:
            ai_response = get_product_catalog()
        
        elif message_text.startswith("order "):
            # Extract order details
            order_details = message_text.split(" ")
            if len(order_details) >= 3:
                product_name = order_details[1]
                quantity = order_details[2]

                # 🔥 Fetch cart order ID from Interakt API
                cart_id = fetch_cart_id(phone_number)
                
                if cart_id:
                    ai_response = process_payment(phone_number, cart_id)
                else:
                    ai_response = "⚠️ Order not found. Please add items to cart first."
            else:
                ai_response = "⚠️ Invalid format. Please use: *Order [Product Name] [Quantity]*"
        
        elif message_text == "paid":
            ai_response = "✅ Payment received! Your order is confirmed and will be processed shortly."
        
        else:
            ai_response = get_ai_response(message_text)

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
        print(f"🔥 Critical error: {str(e)}", flush=True)
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

def fetch_cart_id(phone_number):
    """Fetch latest cart ID for a customer from Interakt"""
    try:
        response = requests.get(
            "https://api.interakt.ai/v1/public/cart/orders",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            },
            params={"phone_number": phone_number}
        )

        print(f"📡 Interakt Cart API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            cart_orders = response.json().get("data", [])
            if cart_orders:
                latest_cart = cart_orders[-1]  # Get the most recent cart order
                return latest_cart.get("id")
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"🔥 Error fetching cart ID: {str(e)}")
        return None

def process_payment(phone_number, cart_id):
    """Generate payment link using Interakt and send to the customer"""
    try:
        payload = {
            "cart_id": cart_id,
            "payment_mode": "razorpay"
        }

        response = requests.post(
            "https://api.interakt.ai/v1/public/cart/payment_link",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        print(f"📡 Interakt Payment API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            payment_data = response.json()
            payment_link = payment_data.get("payment_link")

            return (
                f"🛒 *Payment Link Generated!*\n"
                f"💰 Please complete your payment here: {payment_link}\n"
                f"Once you've completed the payment, reply *'Paid'* to confirm."
            )
        else:
            return f"⚠️ Failed to generate payment link. Error: {response.text}"
    except Exception as e:
        print(f"🔥 Interakt Payment Error: {str(e)}", flush=True)
        return "⚠️ Error processing payment."

if __name__ == '__main__':
    print(f"\n🚀 Starting WhatsApp AI Assistant on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
