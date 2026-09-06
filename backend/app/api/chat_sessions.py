from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.connection import get_db

from app.database.models import (
    User,
    ChatSession,
)

from app.schemas.chat_session import (
    ChatSessionCreate,
    ChatSessionResponse,
)


router = APIRouter(
    prefix="/api/chat/sessions",
    tags=["Chat Sessions"]
)


@router.post(
    "",
    response_model=ChatSessionResponse
)
def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    session = ChatSession(
        user_id=current_user.id,
        title=session_data.title
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("",response_model=list[ChatSessionResponse])
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),):

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id== current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return sessions

# Get conversation history
from app.database.models import (User,ChatSession,ChatMessage,)

@router.get("/{session_id}/messages")
def get_messages(session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id,
            ChatSession.user_id== current_user.id)
        .first())

    if not session:
        raise HTTPException(
            status_code=404,detail="Chat session not found"
        )

    messages = (db.query(ChatMessage)
        .filter(ChatMessage.session_id== session_id)
        .order_by(ChatMessage.created_at.asc())
        .all())

    return messages
