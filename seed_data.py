from sqlalchemy.orm import Session
from models import engine, Property, PropertyImage, DubaiArea

with Session(engine) as session:
    areas = [
        DubaiArea(name="Dubai Marina", aliases="marina,DM,dubai marina"),
        DubaiArea(name="JBR", aliases="jbr,jumeirah beach,the walk"),
        DubaiArea(name="Business Bay", aliases="bb,biz bay,business bay"),
        DubaiArea(name="Al Nahda", aliases="nahda,al nahda"),
        DubaiArea(name="Bur Dubai", aliases="bur dubai,meena bazaar"),
    ]
    session.add_all(areas)

    props = [
        Property(
            property_type="room", title="Spacious Room in Marina",
            area="Dubai Marina", monthly_rent=2500, gender_preference="male",
            wifi_included=True, dewa_included=True, furnishing="furnished",
        ),
        Property(
            property_type="bed_space", title="Bed Space near JBR Beach",
            area="JBR", monthly_rent=1200, gender_preference="male",
            wifi_included=True, dewa_included=True, furnishing="furnished",
        ),
        Property(
            property_type="room", title="Master Room Business Bay",
            area="Business Bay", monthly_rent=3500, gender_preference="any",
            wifi_included=True, dewa_included=True, parking_included=True,
            furnishing="furnished",
        ),
        Property(
            property_type="partition", title="Partition in Al Nahda",
            area="Al Nahda", monthly_rent=900, gender_preference="male",
            wifi_included=True, furnishing="furnished",
        ),
        Property(
            property_type="room", title="Affordable Room Bur Dubai",
            area="Bur Dubai", monthly_rent=1800, gender_preference="any",
            wifi_included=True, dewa_included=True, furnishing="furnished",
        ),
        Property(
            property_type="room", title="Cozy Room Marina Walk",
            area="Dubai Marina", monthly_rent=3000, gender_preference="female",
            wifi_included=True, dewa_included=True, gym_pool_access=True,
            furnishing="furnished",
        ),
    ]
    session.add_all(props)
    session.commit()
    print(f"Seeded {len(areas)} areas and {len(props)} properties")