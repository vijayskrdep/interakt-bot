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

def get_order_status(phone_number):
    """Fetch latest order status for a customer from Interakt"""
    try:
        response = requests.get(
            "https://api.interakt.ai/v1/public/cart/orders",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            },
            params={"phone_number": phone_number}
        )

        print(f"\n📡 Interakt Order Status API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            orders = response.json().get("data", [])
            if orders:
                latest_order = orders[-1]  # Get the most recent order
                status = latest_order.get("order_status", "Unknown")
                tracking_url = latest_order.get("tracking_url", "Not Available")
                
                return (
                    f"📦 *Order Update:*\n"
                    f"🚚 Current Status: {order_status}\n"
                    f"🛒 Order ID: {order_id}\n"
                    f"🔗 Track your order: {tracking_link}"

                    "Thank you for shopping with us!"
                )
            else:
                return "⚠️ No recent orders found."
        else:
            return "⚠️ Unable to fetch order status. Try again later."
    except Exception as e:
        print(f"🔥 Error fetching order status: {str(e)}")
        return "⚠️ Error retrieving order status."

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
                "model": "gpt-4-turbo",
                "messages": [
                    {"role": "system", "content": "You are a professional customer assistant for Sundarban JFMC. You handle inquiries about honey, ghee, orders, payment, and delivery tracking."},
                    {"role": "user", "content": prompt}
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

        event_type = data.get("type")
        customer_data = data.get("data", {}).get("customer", {})
        phone_number = customer_data.get("country_code", "") + customer_data.get("phone_number", "")
        message_data = data.get("data", {}).get("message", {})
        message_text = message_data.get("message", "").strip().lower()

        print(f"📩 Received Message: {message_text} from {phone_number}")

        if event_type == "message_received":
            if "track order" in message_text or "delivery status" in message_text:
                ai_response = get_order_status(phone_number)
            else:
                ai_response = get_ai_response(message_text)
        elif event_type in ["order_shipped", "order_out_for_delivery", "order_delivered"]:
            ai_response = get_order_status(phone_number)
        else:
            return jsonify({"status": "ignored", "message": "Event ignored"}), 200

        response = requests.post(
            "https://api.interakt.ai/v1/public/message/",
            headers={"Authorization": f"Basic {INTERAKT_API_KEY}", "Content-Type": "application/json"},
            json={"fullPhoneNumber": phone_number, "type": "Text", "data": {"message": ai_response}}
        )

        print(f"📡 Interakt Response: {response.status_code} - {response.text}")

        return jsonify({"status": "success", "message": "Message sent"}), 200
    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    print(f"\n🚀 Starting WhatsApp AI Assistant on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
