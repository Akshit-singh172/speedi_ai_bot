import requests
from dotenv import load_dotenv
import os

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_products():
    """Fetch all products"""
    res = requests.get(f"{BACKEND_URL}/api/products", timeout=5)
    if not res.ok:
        raise Exception(f"Products API failed: {res.text}")
    return res.json()


def get_orders(user_id: str):
    """Fetch user orders"""
    res = requests.get(
        f"{BACKEND_URL}/orders",
        params={"user_id": user_id},
        timeout=5
    )
    if not res.ok:
        raise Exception(f"Orders API failed: {res.text}")
    return res.json()

def make_cart(items):
    if not items or not isinstance(items, list):
        raise Exception("Invalid cart format")

    validated_cart = []

    for item in items:
        name = item.get("item")
        quantity = item.get("quantity", 1)

        if not name:
            continue

        validated_cart.append({
            "item": name,
            "quantity": quantity
        })

    return {
        "status": "success",
        "cart": validated_cart
    }


def handle_tool_call(tool_name, args):
    # Initialize a standard response structure
    result_data = None
    msg = "Action completed successfully"
    resp_type = "message"

    if tool_name == "get_products":
        result_data = get_products()
        resp_type = "products"
        msg = "Fetched available products."

    elif tool_name == "get_orders":
        # Ensure user_id is passed correctly
        result_data = get_orders(args.get("user_id"))
        resp_type = "orders"
        msg = f"Found {len(result_data) if result_data else 0} past orders."

    elif tool_name == "make_cart":
        result_data = make_cart(args.get("items"))
        resp_type = "cart"
        msg = "Items successfully added to your cart."

    # Standardize the output for the API
    return {
        "type": resp_type,
        "message": msg,
        # Force data to be an array so frontend Array.isArray() stays happy
        "data": result_data if isinstance(result_data, list) else [result_data] if result_data else []
    }