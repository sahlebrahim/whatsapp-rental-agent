from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime


Base = declarative_base()
engine = create_engine("sqlite:///rental.db", echo=True)

class DubaiArea(Base):
    __tablename__ = "dubai_areas"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    aliases = Column(Text, nullable=True)



class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    property_type = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    area = Column(String(100), nullable=False)
    monthly_rent = Column(Float, nullable=False)
    gender_preference = Column(String(10), default="any")

    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    furnishing = Column(String(20), default="furnished")

    wifi_included = Column(Boolean, default=False)
    dewa_included = Column(Boolean, default=False)
    parking_included = Column(Boolean, default=False)
    gym_pool_access = Column(Boolean, default=False)

    deposit_amount = Column(Float, nullable=True)
    minimum_stay_months = Column(Integer, default=1)
    payment_frequency = Column(String(20), default="monthly")
    cheques = Column(Integer, default=1)

    couples_allowed = Column(Boolean, default=False)
    smoking_allowed = Column(Boolean, default=False)
    pets_allowed = Column(Boolean, default=False)

    landlord_name = Column(String(100), nullable=True)
    landlord_phone = Column(String(20), nullable=True)

    status = Column(String(20), default="available")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_chat_summary(self):
        amenities = []
        if self.wifi_included:
            amenities.append("WiFi")
        if self.dewa_included:
            amenities.append("DEWA")
        if self.parking_included:
            amenities.append("Parking")
        if self.gym_pool_access:
            amenities.append("Gym/Pool")

        summary = f"*{self.title}*\n"
        summary += f"📍 {self.area}\n"
        summary += f"💰 AED {self.monthly_rent:,.0f}/month\n"
        summary += f"🏠 {self.property_type.replace('_', ' ').title()}\n"

        if amenities:
            summary += f"✅ {', '.join(amenities)}\n"

        if self.gender_preference != "any":
            summary += f"👤 {self.gender_preference.title()} only\n"

        return summary
    
class PropertyImage(Base):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    caption = Column(String(200), nullable=True)
    display_order = Column(Integer, default=0)
    is_hero = Column(Boolean, default=False)