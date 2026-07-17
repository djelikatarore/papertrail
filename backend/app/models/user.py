from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(String, nullable=False)

    created_at = Column(String, nullable=True)

    workspace_memberships = relationship(
        "WorkspaceMember",
        back_populates="user"
    )

    review_comments = relationship(
        "ReviewComment",
        back_populates="user"
    )