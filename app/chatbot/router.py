from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.auth.router import get_current_user
from app.chatbot.engine import ChatbotEngine

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Create a global chatbot engine instance
chatbot_engine = ChatbotEngine()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None

class ChatHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    createdAt: Any

class ChatSessionInfo(BaseModel):
    id: str
    title: str
    createdAt: Any
    updatedAt: Any

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Process chat message and return response"""
    try:
        response = await chatbot_engine.chat(current_user["id"], request.message)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )

@router.put("/chat/{session_id}", response_model=ChatResponse)
async def chat_sesion(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Process chat message and return response"""
    try:
        response = await chatbot_engine.chat(current_user["id"], request.message)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )

@router.post("/refresh-index")
async def refresh_index(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Refresh the chatbot's knowledge index"""
    # Check if user is admin
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can refresh the index"
        )
    
    try:
        result = await chatbot_engine.refresh_index()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing index: {str(e)}"
        )

@router.get("/history", response_model=List[ChatSessionInfo])
async def get_chat_history(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get chat history for the current user"""
    from app.db.prisma_client import get_prisma
    
    try:
        async with get_prisma() as prisma:
            chat_sessions = await prisma.titlechat.find_many(
                where={
                    'userId': current_user["id"]
                },
            order=[
                {
                    'createdAt': 'desc'
                }
            ]
            )
            
            return [
                ChatSessionInfo(
                    id=session.id,
                    title=session.title,
                    createdAt=session.createdAt,
                    updatedAt=session.updatedAt
                )
                for session in chat_sessions
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}"
        )

@router.get("/history/{session_id}", response_model=List[ChatHistoryItem])
async def get_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get chat messages for a specific session"""
    from app.db.prisma_client import get_prisma
    
    try:
        async with get_prisma() as prisma:
            # Verify the session belongs to the user
            session = await prisma.titlechat.find_first(
                where={
                    'id': session_id,
                    'userId': current_user["id"]
                }
            )
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            # Get chat messages
            messages = await prisma.chat.find_many(
                where={
                    'titleChatId': session_id
                },
                order=[
                {
                    'createdAt': 'asc'
                }
            ]
            )
            
            return [
                ChatHistoryItem(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    createdAt=msg.createdAt
                )
                for msg in messages
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat session: {str(e)}"
        )