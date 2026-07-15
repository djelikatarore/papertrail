from sqlalchemy import Column, Integer, String
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    raw_text = Column(String, nullable=True)
    status = Column(String, default="PROCESSING")
    read_status = Column(String, default="UNREAD")
    review_type = Column(String, nullable=True)
    contribution = Column(String, nullable=True)
    methodology = Column(String, nullable=True)
    key_results = Column(String, nullable=True)
    limitations = Column(String, nullable=True)
    keywords = Column(String, nullable=True)
    embedding = Column(String, nullable=True)