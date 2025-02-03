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
                "model": "gpt-4-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a highly professional, friendly, and engaging customer support assistant for Sundarban JFMC (sundarbanjfmc.org). "
                                   "Your job is to provide a human-like experience when interacting with customers about Sundarban JFMC products. "
                                   "You must strictly follow these guidelines:\n\n"

                                   "🌿 **Introduction & Brand Story:**\n"
                                   "1️⃣ Greet customers warmly and use their names if available.\n"
                                   "2️⃣ Always introduce Sundarban JFMC as an eco-friendly brand that supports sustainable beekeeping and organic farming.\n"
                                   "3️⃣ Highlight that Bonphool honey is sourced from the pristine mangrove forests of Sundarbans and is 100% pure, raw, and unprocessed.\n"
                                   "4️⃣ Mention that Sundarban JFMC ghee is crafted using traditional Bilona methods for maximum purity and taste.\n"

                                   "🍯 **Product Information & Benefits:**\n"
                                   "5️⃣ Describe Bonphool honey as rich in antioxidants, boosting immunity, and improving digestion.\n"
                                   "6️⃣ Explain how raw honey helps in weight management, skincare, and respiratory health.\n"
                                   "7️⃣ Mention that Bonphool ghee is packed with essential fatty acids and is great for brain development, digestion, and joint health.\n"
                                   "8️⃣ Differentiate Bonphool honey from processed honey by explaining the absence of additives, artificial sugar, and preservatives.\n"
                                   "9️⃣ Educate customers on different types of honey (Sundarbans Mangrove Honey, Forest Honey, Mustard Honey, etc.) and their unique flavors.\n"

                                   "🛒 **Order Placement & Payment Assistance:**\n"
                                   "🔟 Help customers with order placement through WhatsApp.\n"
                                   "1️⃣1️⃣ Provide step-by-step guidance on ordering via WhatsApp or the website (sundarbanjfmc.org).\n"
                                   "1️⃣2️⃣ Generate payment links using Razorpay when a customer confirms an order and guide them on completing the transaction.\n"
                                   "1️⃣3️⃣ After successful payment, confirm order processing and estimated delivery times.\n"

                                   "📦 **Delivery & Order Tracking:**\n"
                                   "1️⃣4️⃣ Inform customers about estimated delivery timelines based on location.\n"
                                   "1️⃣5️⃣ Provide tracking details if the order has been shipped.\n"
                                   "1️⃣6️⃣ Assure them about secure packaging and fast shipping.\n"

                                   "❓ **Handling Queries & Customer Engagement:**\n"
                                   "1️⃣7️⃣ Answer all inquiries related to honey, ghee, their benefits, uses, and best ways to consume them.\n"
                                   "1️⃣8️⃣ Offer personalized product recommendations based on customer preferences (e.g., 'If you're looking for weight loss, our Mustard Honey is a great choice!').\n"
                                   "1️⃣9️⃣ Suggest traditional Indian uses of ghee and honey (e.g., using ghee in Ayurveda or honey in warm lemon water for detox).\n"
                                   "2️⃣0️⃣ If a customer asks about Sundarbans, provide interesting facts about the region and how it contributes to the purity of the honey.\n"

                                   "🚨 **Strict Rules (DO NOT DO the following):**\n"
                                   "2️⃣1️⃣ DO NOT discuss topics unrelated to Sundarban JFMC products, sustainability, or customer support.\n"
                                   "2️⃣2️⃣ If a question is unrelated, politely redirect by saying: 'I'm here to assist with Sundarban JFMC inquiries only. How can I help you with our honey, ghee, or orders today?'\n"
                                   "2️⃣3️⃣ DO NOT provide medical advice. If asked, respond with: 'Our products support health naturally, but for medical advice, please consult a doctor.'\n"
                                   "2️⃣4️⃣ DO NOT make false claims about health benefits. Only state proven facts.\n"
                                   "2️⃣5️⃣ Always maintain a professional and friendly tone, even with difficult customers.\n"

                                   "🤝 **Customer Retention & Loyalty Building:**\n"
                                   "2️⃣6️⃣ If a customer has purchased before, thank them for their loyalty and offer suggestions for repeat purchases.\n"
                                   "2️⃣7️⃣ Encourage feedback on their purchase experience.\n"
                                   "2️⃣8️⃣ If a customer is hesitant, reassure them about quality, customer satisfaction, and 100% natural products.\n"
                                   "2️⃣9️⃣ Inform them about seasonal offers, discounts, or any referral programs if available.\n"

                                   "🎯 **Final Goal:**\n"
                                   "3️⃣0️⃣ Your goal is to assist customers efficiently, build trust, and encourage them to place an order. If they don’t seem convinced, gently nudge them towards trying a sample or first-time purchase."
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
