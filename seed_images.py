from sqlalchemy.orm import Session
from models import engine, Property, PropertyImage

R2_BASE = "https://pub-baa797c30a864b248e2b35509974b788.r2.dev"

property_image_map = {
    "Spacious Room in Marina":      "ahli_master.jpg",
    "Bed Space near JBR Beach":     "muwailah_bedroom.jpeg",
    "Master Room Business Bay":     "ahli_hall.jpg",
    "Partition in Al Nahda":        "shalu_room.jpeg",
    "Affordable Room Bur Dubai":    "zarooni_hall.jpeg",
    "Cozy Room Marina Walk":        "ahli_balcony.jpg",
}

with Session(engine) as session:
    for title, filename in property_image_map.items():
        prop = session.query(Property).filter_by(title=title).first()
        if not prop:
            print(f"property not found: {title}")
            continue

        existing = (
            session.query(PropertyImage)
            .filter_by(property_id=prop.id, is_hero=True)
            .first()
        )
        if existing:
            print(f"skipped {title}, hero exists")
            continue

        hero = PropertyImage(
            property_id=prop.id,
            image_url=f"{R2_BASE}/{filename}",
            caption=f"{prop.title} - main photo",
            display_order=1,
            is_hero=True,
        )
        session.add(hero)
        print(f"added {filename} for {title}")

    session.commit()
    print("done")