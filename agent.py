from google import genai
from google.genai import types # Use types for strict schema support
from dotenv import load_dotenv
import os
import re
import json

def extract_json_array(text):
    """
    Finds the first JSON array [...] in a string and returns it as a list.
    """
    try:
        # Regex to find everything between the first '[' and last ']'
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing JSON array: {e}")
    
    return [] # Return empty list if no valid array is found

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Use the Client with the appropriate API version if needed
client = genai.Client(api_key=GEMINI_API_KEY)

# TOOL DEFINITIONS
# 1. Products Tool
get_products_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_products",
            description="Get all available grocery products",
            parameters=types.Schema(type="OBJECT", properties={})
        )
    ]
)

# 2. Orders Tool
get_orders_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_orders",
            description="Get user's past orders",
            parameters=types.Schema(
                type="OBJECT",
                properties={"user_id": types.Schema(type="STRING")},
                required=["user_id"]
            )
        )
    ]
)

# 3. Cart Tool
make_cart_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="make_cart",
            description="Create a shopping cart using selected products",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "items": types.Schema(
                        type="ARRAY",
                        items=types.Schema(
                            type="OBJECT",
                            properties={
                                "item": types.Schema(type="STRING"),
                                "quantity": types.Schema(type="INTEGER")
                            },
                            required=["item", "quantity"]
                        )
                    )
                },
                required=["items"]
            )
        )
    ]
)

def load_prompt():
    with open("prompt.txt", "r", encoding="utf-8") as file:
        return file.read()

SYSTEM_PROMPT = load_prompt()

def run_agent(user_prompt: str, user_id: str):
    # Pass all individual tools in a list
    config = types.GenerateContentConfig(
        system_instruction= SYSTEM_PROMPT, 
        tools=[get_products_tool, get_orders_tool, make_cart_tool],
    )

    chat = client.chats.create(model="gemini-2.5-flash", config=config)
    response = chat.send_message(user_prompt)

    # Manual Tool Loop
    while response.candidates[0].content.parts[0].function_call:
        fc = response.candidates[0].content.parts[0].function_call
        tool_name = fc.name
        
        # Convert the Protobuf Struct to a standard Python dict
        args = dict(fc.args)

        if tool_name == "get_orders":
            args["user_id"] = user_id

        from tools import handle_tool_call
        result = handle_tool_call(tool_name, args)

        # Immediate exit for 'make_cart' if your backend logic requires it
        if tool_name == "make_cart":
            return {
                "type": "cart",
                "message": "🛒 Items added to your cart",
                "data": result.get("data", []) # Matches your standardized backend
            }

        response = chat.send_message(
            types.Part.from_function_response(
                name=tool_name,
                response=result
            )
        )

    # FINAL PARSING LOGIC
    full_text = response.text

    # Extracting the type based on the prompt tags
    if "CART:" in full_text:
        return {
            "type": "cart",
            "message": "Cart created!",
            "data": extract_json_array(full_text)
        }
    
    if "PRODUCTS:" in full_text:
        return {
            "type": "products",
            "message": "Check out these items:",
            "data": extract_json_array(full_text)
        }

    return {
        "type": "message",
        "data": full_text
    }