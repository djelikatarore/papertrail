from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
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
    text_blocks = relationship("TextBlock", back_populates="paper")
    visual_elements = relationship("VisualElement", back_populates="paper")



class TextBlock(Base):
    __tablename__ = "text_blocks"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    text = Column(String, nullable=False)
    paper = relationship("Paper", back_populates="text_blocks")
    

class VisualElement(Base):
    __tablename__ = "visual_elements"
    id = Column(Integer, primary_key=True, index=True)

    paper_id = Column(Integer, ForeignKey("papers.id"))
    element_type = Column(String, nullable=True)
    content = Column(String, nullable=True)

    paper = relationship("Paper", back_populates="visual_elements")