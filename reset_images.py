from sqlalchemy.orm import Session
from models import engine, PropertyImage

with Session(engine) as session:
       count = session.query(PropertyImage).count()
       session.query(PropertyImage).delete()
       session.commit()
       print(f"deleted {count} image rows")