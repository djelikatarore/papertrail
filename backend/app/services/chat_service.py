from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession


def get_or_create_paper_session(paper_id: int, title: str, db: Session) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.paper_id == paper_id, ChatSession.project_id.is_(None))
        .first()
    )
    if session:
        return session

    session = ChatSession(paper_id=paper_id, title=title, created_at=datetime.now(timezone.utc).isoformat())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_or_create_project_session(project_id: int, title: str, db: Session) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.project_id == project_id, ChatSession.paper_id.is_(None))
        .first()
    )
    if session:
        return session

    session = ChatSession(project_id=project_id, title=title, created_at=datetime.now(timezone.utc).isoformat())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def save_exchange(session_id: int, question: str, answer: str, db: Session) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db.add(ChatMessage(session_id=session_id, role="user", content=question, created_at=now))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=answer, created_at=now))
    db.commit()


def get_history_grouped_by_date(session: ChatSession, db: Session) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id)
        .all()
    )

    grouped: dict[str, list[ChatMessage]] = {}
    for message in messages:
        date_key = (message.created_at or "")[:10] or "unknown"
        grouped.setdefault(date_key, []).append(message)

    return [
        {
            "date": date_key,
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at}
                for m in date_messages
            ],
        }
        for date_key, date_messages in sorted(grouped.items())
    ]
