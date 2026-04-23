import json
import os
import httpx
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from openai import OpenAI
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from queries import search_properties, resolve_area
from models import engine, Property, PropertyImage

load_dotenv()
app = FastAPI()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

last_results = {}

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

        if "area" in args:
            args["area"] = resolve_area(args["area"])

        results = search_properties(**args)

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

    return message.content, []


@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"error": "Invalid token"}


@app.get("/property/{property_id}", response_class=HTMLResponse)
async def property_gallery(property_id: int):
    with Session(engine) as session:
        prop = session.query(Property).filter_by(id=property_id).first()
        if not prop:
            return HTMLResponse("<h1>Property not found</h1>", status_code=404)
        images = sorted(prop.images, key=lambda i: i.display_order)

    amenities = []
    if prop.wifi_included:
        amenities.append("WiFi")
    if prop.dewa_included:
        amenities.append("DEWA")
    if prop.parking_included:
        amenities.append("Parking")
    if prop.gym_pool_access:
        amenities.append("Gym/Pool")

    amenities_html = ", ".join(amenities) if amenities else "None listed"
    gender_html = f"{prop.gender_preference.title()} only" if prop.gender_preference != "any" else "Any gender"
    images_html = "".join(
        f'<img src="{img.image_url}" alt="{img.caption or prop.title}" loading="lazy"/>'
        for img in images
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{prop.title}</title>
<style>
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; color: #222; }}
  .header {{ padding: 20px 16px; background: #fff; border-bottom: 1px solid #e0e0e0; }}
  .header h1 {{ margin: 0 0 8px 0; font-size: 20px; }}
  .header .meta {{ color: #555; font-size: 14px; line-height: 1.6; }}
  .header .meta div {{ margin: 2px 0; }}
  .price {{ font-size: 18px; font-weight: 600; color: #2a7; margin: 8px 0; }}
  .gallery {{ display: flex; flex-direction: column; gap: 2px; background: #000; }}
  .gallery img {{ width: 100%; display: block; }}
  .empty {{ padding: 40px 16px; text-align: center; color: #888; }}
</style>
</head>
<body>
  <div class="header">
    <h1>{prop.title}</h1>
    <div class="price">AED {prop.monthly_rent:,.0f}/month</div>
    <div class="meta">
      <div>Location: {prop.area}</div>
      <div>Type: {prop.property_type.replace('_', ' ').title()}</div>
      <div>Includes: {amenities_html}</div>
      <div>For: {gender_html}</div>
    </div>
  </div>
  <div class="gallery">
    {images_html if images_html else '<div class="empty">No photos available yet</div>'}
  </div>
</body>
</html>"""
    return HTMLResponse(html)


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

        if not text:
            return {"status": "no text"}

        if text.lower().startswith("stress test"):
            parts = text.split()
            try:
                n = int(parts[-1])
            except ValueError:
                n = 10
            await stress_test(phone, n)
            return {"status": "ok"}

        stripped = text.strip()
        if stripped.isdigit() and phone in last_results:
            idx = int(stripped)
            if 1 <= idx <= len(last_results[phone]):
                prop_id = last_results[phone][idx - 1]
                await send_more_photos(phone, prop_id)
                return {"status": "ok"}

        reply, properties = await get_ai_response(text, phone)

        if properties:
            shown = properties[:3]
            property_ids = []

            for idx, prop in enumerate(shown, 1):
                hero = next((img for img in prop.images if img.is_hero), None)
                if not hero and prop.images:
                    hero = prop.images[0]

                caption = f"[{idx}] {prop.to_chat_summary()}"

                if hero:
                    await send_whatsapp_image(phone, hero.image_url, caption)
                else:
                    await send_whatsapp_message(phone, caption)

                property_ids.append(prop.id)

            last_results[phone] = property_ids

            if len(property_ids) == 1:
                hint = "Reply 1"
            elif len(property_ids) == 2:
                hint = "Reply 1 or 2"
            else:
                nums = ", ".join(str(i) for i in range(1, len(property_ids)))
                hint = f"Reply {nums} or {len(property_ids)}"

            await send_whatsapp_message(
                phone,
                f"{hint} to see more photos of that listing."
            )
        else:
            await send_whatsapp_message(phone, reply)

    except Exception as e:
        print(f"webhook error: {type(e).__name__}: {e}")

    return {"status": "ok"}


async def send_more_photos(phone, property_id):
    with Session(engine) as session:
        prop = session.query(Property).filter_by(id=property_id).first()
        if not prop:
            await send_whatsapp_message(phone, "Sorry, that listing is no longer available.")
            return

        images = (
            session.query(PropertyImage)
            .filter_by(property_id=property_id, is_hero=False)
            .order_by(PropertyImage.display_order)
            .all()
        )

        if not images:
            await send_whatsapp_message(phone, "No additional photos available for this listing.")
            return

        title = prop.title
        total = len(images)

    await send_whatsapp_message(phone, f"{total} more photos of *{title}*:")

    for i, img in enumerate(images, 1):
        caption = f"{i}/{total}"
        await send_whatsapp_image(phone, img.image_url, caption)

    await send_whatsapp_message(
        phone,
        f"All photos for *{title}*.\n"
        f"Full gallery: https://rag.sahlebrahim.com/property/{property_id}\n\n"
        f"Search again or ask me anything."
    )


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
        await client.post(url, json=payload, headers=headers)


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
        await client.post(url, json=payload, headers=headers)


async def stress_test(phone, n):
    with Session(engine) as session:
        images = session.query(PropertyImage).limit(n).all()
        urls_and_captions = [(img.image_url, f"{i}/{len(images)}") for i, img in enumerate(images, 1)]

    for url, caption in urls_and_captions:
        api_url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {"link": url, "caption": caption}
        }
        async with httpx.AsyncClient() as client:
            await client.post(api_url, json=payload, headers=headers)