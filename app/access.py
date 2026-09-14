from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelGrant, ModelProject, User


def can_manage_project(project: ModelProject, user: User) -> bool:
    return user.role == "admin" or project.owner_id == user.id


def get_grant(project: ModelProject, user: User, db: Session) -> ModelGrant | None:
    return db.scalar(
        select(ModelGrant).where(
            ModelGrant.project_id == project.id,
            ModelGrant.user_id == user.id,
        )
    )


def can_view_project(project: ModelProject, user: User, db: Session) -> bool:
    return (
        project.visibility == "public"
        or can_manage_project(project, user)
        or get_grant(project, user, db) is not None
    )


def can_infer_project(project: ModelProject, user: User, db: Session) -> bool:
    if project.visibility == "public" or can_manage_project(project, user):
        return True
    grant = get_grant(project, user, db)
    return bool(grant and grant.can_infer)
