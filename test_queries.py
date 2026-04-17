from queries import search_properties, resolve_area

print("=== Area Resolution ===")
print(f"'DM' -> {resolve_area('DM')}")
print(f"'marina' -> {resolve_area('marina')}")
print(f"'bb' -> {resolve_area('bb')}")
print(f"'random' -> {resolve_area('random')}")

print("\n=== Rooms in Marina under 3000 ===")
results = search_properties(area="Dubai Marina", max_rent=3000, property_type="room")
for p in results:
    print(p.to_chat_summary())

print("\n=== Male listings under 2000 ===")
results = search_properties(max_rent=2000, gender="male")
for p in results:
    print(p.to_chat_summary())

print("\n=== Everything in Business Bay ===")
results = search_properties(area="Business Bay")
for p in results:
    print(p.to_chat_summary())