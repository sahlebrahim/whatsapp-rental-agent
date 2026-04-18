from sqlalchemy.orm import Session, joinedload
from models import engine, Property, PropertyImage, DubaiArea


def search_properties(area=None, max_rent=None, min_rent=None,
                      property_type=None, gender=None, limit=5):
    with Session(engine) as session:
        query = (
            session.query(Property)
            .options(joinedload(Property.images))
            .filter(Property.status == "available")
        )

        if area:
            query = query.filter(Property.area.ilike(f"%{area}%"))

        if max_rent:
            query = query.filter(Property.monthly_rent <= max_rent)

        if min_rent:
            query = query.filter(Property.monthly_rent >= min_rent)

        if property_type:
            query = query.filter(Property.property_type == property_type)

        if gender:
            query = query.filter(
                Property.gender_preference.in_([gender, "any"])
            )

        results = query.order_by(Property.monthly_rent.asc()).limit(limit).unique().all()
        return results


def resolve_area(user_input):
    with Session(engine) as session:
        areas = session.query(DubaiArea).all()
        user_input_lower = user_input.lower().strip()

        for area in areas:
            if user_input_lower == area.name.lower():
                return area.name

            if area.aliases:
                alias_list = [a.strip().lower() for a in area.aliases.split(",")]
                if user_input_lower in alias_list:
                    return area.name

        return user_input