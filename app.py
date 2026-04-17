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
        print(f"tool call hit >> {tool_call.function.name} with {args}")

        if "area" in args:
            args["area"] = resolve_area(args["area"])
            print(f"area resolved to >> {args['area']}")

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

        return final_response.choices[0].message.content

    print(f"no tool call, just vibes")
    return message.content


@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"error": "Invalid token"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no message"}

        message = value["messages"][0]
        phone = message["from"]
        text = message.get("text", {}).get("body", "")
        print(f"msg from {phone} >> {text}")

        if not text:
            return {"status": "no text"}

        reply = await get_ai_response(text, phone)
        print(f"replying >> {reply[:80]}...")
        await send_whatsapp_message(phone, reply)

    except (KeyError, IndexError) as e:
        print(f"something broke >> {e}")

    return {"status": "ok"}


async def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers)
        print(f"wa api >> {r.status_code}")