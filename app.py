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
        import json
        print("\n📥 Incoming Webhook JSON (Raw):\n", json.dumps(data, indent=4))

        if data.get("type") == "Webhook Test":
            print("⚠️ Received a test webhook, ignoring...")
            return jsonify({"status": "ignored", "message": "Webhook test event ignored"}), 200

        if data.get("type") != "message_received":
            print("⚠️ Ignoring non-message events...")
            return jsonify({"status": "ignored", "message": "Non-message event ignored"}), 200

        customer_data = data.get("data", {}).get("customer", {})
        phone_number = customer_data.get("country_code", "") + customer_data.get("phone_number", "")
        message_data = data.get("data", {}).get("message", {})
        message_text = message_data.get("message")

        if "product" in message_text.lower() or "catalog" in message_text.lower() or "list" in message_text.lower():
            ai_response = get_product_catalog()
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
        return jsonify({"status": "success", "message": "Message sent"}), 200
    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    print("\n🚀 Starting WhatsApp AI Assistant...")
    app.run(host='0.0.0.0', port=PORT)
