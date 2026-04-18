import json
import os
import httpx
from fastapi import FastAPI, Request
from openai import OpenAI
from queries import search_properties, resolve_area
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": "Search for rental properties in Dubai. Use when a user is looking for accommodation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "description": "Area in Dubai like Marina, JBR, Business Bay, Al Nahda"},
                    "max_rent": {"type": "number", "description": "Maximum monthly rent in AED"},
                    "min_rent": {"type": "number", "description": "Minimum monthly rent in AED"},
                    "property_type": {"type": "string", "enum": ["bed_space", "room", "partition", "studio", "apartment"], "description": "Type of property"},
                    "gender": {"type": "string", "enum": ["male", "female"], "description": "Gender of the tenant"}
                }
            }
        }
    }
]

SYSTEM_PROMPT = """You are a Dubai rental property assistant on WhatsApp. 
You help tenants find rooms, bed spaces, partitions, and apartments.
When a user describes what they're looking for, use the search_properties tool.
Keep responses short and friendly - this is WhatsApp, not email.
If the user greets you, greet back and ask what they're looking for.
Always resolve area nicknames: DM=Dubai Marina, BB=Business Bay, etc."""


async def get_ai_response(user_message, phone_number):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
    )

    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        print(f"tool call: {tool_call.function.name} args={args}")

        if "area" in args:
            args["area"] = resolve_area(args["area"])
            print(f"area resolved: {args['area']}")

        results = search_properties(**args)
        print(f"db returned {len(results)} listings")

        if results:
            listings = "\n\n".join([p.to_chat_summary() for p in results])
            tool_result = f"Found {len(results)} listings:\n\n{listings}"
        else:
            tool_result = "No properties found matching those criteria."

        messages.append(message.model_dump())
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
        })

        final_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        return final_response.choices[0].message.content, results

    print("no tool call")
    return message.content, []


@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"error": "Invalid token"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no message"}

        message = value["messages"][0]
        phone = message["from"]
        text = message.get("text", {}).get("body", "")
        print(f"incoming from {phone}: {text}")

        if not text:
            return {"status": "no text"}

        reply, properties = await get_ai_response(text, phone)
        print(f"reply: {reply[:80]}")

        if properties:
            for prop in properties[:3]:
                hero = next((img for img in prop.images if img.is_hero), None)
                if not hero and prop.images:
                    hero = prop.images[0]

                if hero:
                    caption = prop.to_chat_summary()
                    await send_whatsapp_image(phone, hero.image_url, caption)
                else:
                    await send_whatsapp_message(phone, prop.to_chat_summary())
        else:
            await send_whatsapp_message(phone, reply)

    except Exception as e:
        print(f"webhook error: {type(e).__name__}: {e}")

    return {"status": "ok"}


async def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers)
        print(f"wa text: {r.status_code}")


async def send_whatsapp_image(to, image_url, caption=""):
    url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": image_url, "caption": caption}
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers)
        print(f"wa image: {r.status_code} {r.text[:200]}")