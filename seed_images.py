from sqlalchemy.orm import Session
from models import engine, Property, PropertyImage

R2_BASE = "https://pub-baa797c30a864b248e2b35509974b788.r2.dev"

property_images = {
    "Spacious Room in Marina":    ("ahli_master",   5,  "jpg"),
    "Bed Space near JBR Beach":   ("muweilah",      8,  "jpeg"),
    "Master Room Business Bay":   ("ahli_hall",     8,  "jpg"),
    "Partition in Al Nahda":      ("shalu_room",    10, "jpeg"),
    "Affordable Room Bur Dubai":  ("zarooni_hall",  10, "jpeg"),
    "Cozy Room Marina Walk":      ("ahli_balcony",  8,  "jpg"),
}

with Session(engine) as session:
    for title, (prefix, count, ext) in property_images.items():
        prop = session.query(Property).filter_by(title=title).first()
        if not prop:
            print(f"property not found: {title}")
            continue

        for i in range(1, count + 1):
            filename = f"{prefix}_{i}.{ext}"
            img = PropertyImage(
                property_id=prop.id,
                image_url=f"{R2_BASE}/{filename}",
                caption=None,
                display_order=i,
                is_hero=(i == 1),
            )
            session.add(img)

        print(f"added {count} images for {title}")

    session.commit()
    print("done")