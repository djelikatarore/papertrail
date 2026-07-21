from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.utils.auth_dependency import get_current_user
from app.utils.workspace_access import get_workspace_or_404, require_member

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str | None = None


class UpdateProjectRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    topic: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: int
    workspace_id: int
    title: str
    topic: str
    description: str | None
    status: str
    created_at: str | None

    class Config:
        from_attributes = True


def _get_project_or_404(workspace_id: int, project_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.workspace_id == workspace_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    workspace_id: int,
    payload: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    project = Project(
        workspace_id=workspace_id,
        title=payload.title,
        topic=payload.topic,
        description=payload.description,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    return db.query(Project).filter(Project.workspace_id == workspace_id).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    return _get_project_or_404(workspace_id, project_id, db)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    workspace_id: int,
    project_id: int,
    payload: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete a project",
        )

    db.delete(project)
    db.commit()
