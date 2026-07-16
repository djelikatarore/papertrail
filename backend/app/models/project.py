from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    topic = Column(String, nullable=False)

    description = Column(String, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="ACTIVE"
    )

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    created_at = Column(
        String,
        nullable=True
    )