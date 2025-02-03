import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

# =============================================
#           CONFIGURE ENVIRONMENT VARIABLES
# =============================================
INTERAKT_API_KEY = os.getenv("INTERAKT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
# =============================================

app = Flask(__name__)

def send_whatsapp_message(phone_number, message):
    """Universal message sender through Interakt"""
    try:
        response = requests.post(
            "https://api.interakt.ai/v1/public/message/",
            headers={
                "Authorization": f"Basic {INTERAKT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "fullPhoneNumber": phone_number,
                "type": "Text",
                "data": {"message": message}
            }
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Message sending failed: {str(e)}")
        return False

def handle_order_update(order_data):
    """Automatically process order status updates"""
    try:
        # Extract customer phone number
        phone_data = order_data.get("customer_phone_number", {})
        phone_number = f"{phone_data.get('country_code', '')}{phone_data.get('phone_number', '')}"
        
        # Get order details
        order_id = order_data.get("id")
        order_status = order_data.get("order_status", "").upper()
        tracking_link = order_data.get("tracking_link", "")
        
        # Generate automated message based on status
        status_messages = {
            "CONFIRMED": f"📦 *Order Confirmed!*\n\nOrder ID: {order_id}\nStatus: Your order has been successfully confirmed!",
            "SHIPPED": f"🚚 *Order Shipped!*\n\nOrder ID: {order_id}\nTracking: {tracking_link or 'Will be updated soon'}",
            "DELIVERED": f"🎉 *Order Delivered!*\n\nOrder ID: {order_id}\nThank you for choosing us!",
            "CANCELLED": f"❌ *Order Cancelled*\n\nOrder ID: {order_id}\nContact support for details."
        }
        
        message = status_messages.get(order_status, 
            f"🔄 Order Update\nOrder ID: {order_id}\nStatus: {order_status}")
        
        # Send payment confirmation separately    
        if order_data.get("payment_status") == "PAID":
            send_whatsapp_message(phone_number, f"💳 Payment Received!\nOrder ID: {order_id}\nThank you for your payment!")
        
        return send_whatsapp_message(phone_number, message)
        
    except Exception as e:
        print(f"Order update error: {str(e)}")
        return False

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
    """Fetch the latest order status from Interakt PROPERLY"""
    try:
        # Use the CORRECT API endpoint for order tracking
        response = requests.get(
            "https://api.interakt.ai/v1/public/track/orders",  # Updated endpoint
            headers={
                "Authorization": f"Bearer {INTERAKT_API_KEY}",  # Changed to Bearer token
                "Content-Type": "application/json"
            },
            params={
                "customerPhone": phone_number,  # Correct parameter name
                "sort": "-created_at"  # Get latest order first
            }
        )

        print(f"📡 Interakt Order API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            orders = response.json().get("items", [])  # Correct response structure
            
            if not orders:
                return "📭 No active orders found for this number. Please contact support if you believe this is an error."

            latest_order = orders[0]  # Now properly sorted
            order_id = latest_order.get("orderId", "N/A")
            status = latest_order.get("currentStatus", {}).get("status", "Unknown")
            tracking_url = latest_order.get("trackingUrl", "")
            
            status_map = {
                "CONFIRMED": "📦 Order Confirmed",
                "PROCESSING": "⚙️ Processing",
                "SHIPPED": "🚚 Shipped",
                "OUT_FOR_DELIVERY": "📦 Out for Delivery",
                "DELIVERED": "🎉 Delivered",
                "CANCELLED": "❌ Cancelled"
            }
            
            status_text = status_map.get(status, f"🔄 Status: {status}")
            message = (
                f"📦 *Order #{order_id}*\n"
                f"{status_text}\n"
                f"📅 Last Updated: {latest_order.get('lastUpdated', '')}\n"
            )
            
            if tracking_url:
                message += f"\n🔗 Track Your Package: {tracking_url}"
                
            return message
            
        return f"⚠️ Order tracking unavailable (Error {response.status_code})"
        
    except Exception as e:
        print(f"🔥 Order Tracking Error: {str(e)}")
        return "⚠️ Temporary system error. Please try again later."
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
                        "content": You are an official Sundarban JFMC support assistant. "
               "Always check order status through Interakt before responding. "
               "Never mention technical limitations - provide actual order data."
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
        print("\n📥 Incoming Webhook Type:", data.get("type", "unknown"))
        
        # Handle automated order updates
        if data.get("type") == "cart_order_update":
            order_data = data.get("data", {})
            if handle_order_update(order_data):
                return jsonify({"status": "order_update_processed"}), 200
            return jsonify({"status": "order_update_failed"}), 400
            
        # Handle customer messages
        elif data.get("type") == "message_received":
            customer_data = data.get("data", {}).get("customer", {})
            phone_number = customer_data.get("country_code", "") + customer_data.get("phone_number", "")
            message_text = data.get("data", {}).get("message", {}).get("message", "").lower()

            if not phone_number or not message_text:
                return jsonify({"status": "error", "message": "Missing phone number or message"}), 400

            if "track" in message_text or "order status" in message_text:
                ai_response = get_order_status(phone_number)
            elif "menu" in message_text or "products" in message_text:
                ai_response = get_product_catalog()
            else:
                ai_response = get_ai_response(message_text)

            send_whatsapp_message(phone_number, ai_response)
            return jsonify({"status": "success"}), 200
            
        return jsonify({"status": "ignored"}), 200

    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"\n🚀 WhatsApp Automation with Order Tracking running on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
