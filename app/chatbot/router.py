from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.auth.dependencies import get_current_user
from app.chatbot.engine import ChatbotEngine
from fastapi.requests import Request
import logging

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
# Set up logging for debugging
logger = logging.getLogger(__name__)

# Global chatbot engine instance
chatbot_engine = ChatbotEngine()

# ---------- Request & Response Models ----------

class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    response: str
    sessionId: str
    sources: Optional[List[Dict[str, Any]]] = None

class ChatHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    createdAt: Any

class CreateSessionResponse(BaseModel):
    id: str
    title: str
    createdAt: Any
    updatedAt: Any

class ChatSessionInfo(BaseModel):
    id: str
    title: str
    lastMessage: str
    createdAt: datetime
    updatedAt: datetime
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool
class ChatHistoryResponse(BaseModel):
    data: List[ChatSessionInfo]
    pagination: PaginationInfo

class UpdateTitleRequest(BaseModel):
    title: str

class DeleteSessionResponse(BaseModel):
    message: str



# ---------- Helper Functions ----------

def generate_chat_title(message: str) -> str:
    """Generate chat title based on first message"""
    words = message.split(' ')[:6]  # Take first 6 words
    title = ' '.join(words)
    if len(message.split(' ')) > 6:
        title += '...'
    return title if title else 'New Chat'

# ---------- Endpoints ----------
@router.post("/chat", response_model=ChatResponse) 
async def send_chat_message(
    request_body: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
): 
    # Parse the request body properly
    raw_data = await request_body.json()
    print(f"Raw request data: {raw_data}")
    
    # Extract the nested message data
    message_data = raw_data.get('message', {})
    message_content = message_data.get('message', '')
    session_id = message_data.get('sessionId')  # This might be None
    
    print(f"Received message: {message_content}")
    print(f"Session ID: {session_id}")
    
    """Send a chat message and get AI response""" 
    from app.db.prisma_client import get_prisma 
    print(f"Current user: {current_user}")
    
    if not message_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required"
        )
    
    try: 
        async with get_prisma() as prisma: 
            title_chat_id = session_id 
             
            # If no sessionId provided, create a new chat session 
            if not session_id: 
                print("No sessionId provided, creating a new chat session")
                new_title_chat = await prisma.titlechat.create( 
                    data={ 
                        'title': generate_chat_title(message_content), 
                        'userId': current_user['id']  # Use dict access, not attribute
                    } 
                ) 
                title_chat_id = new_title_chat.id 
                print(f"Created new chat session with ID: {title_chat_id}")
            else: 
                # Verify the session belongs to the user 
                existing_title_chat = await prisma.titlechat.find_first( 
                    where={ 
                        'id': session_id, 
                        'userId': current_user['id']  # Use dict access, not attribute
                    } 
                ) 
                 
                if not existing_title_chat: 
                    raise HTTPException( 
                        status_code=status.HTTP_404_NOT_FOUND, 
                        detail="Chat session not found or access denied" 
                    ) 
                print(f"Using existing chat session with ID: {title_chat_id}")
             
            # Save user message 
            user_message = await prisma.chat.create( 
                data={ 
                    'role': 'USER', 
                    'content': message_content, 
                    'titleChatId': title_chat_id 
                } 
            ) 
             
            # Generate AI response using chatbot engine 
            response_data = await chatbot_engine.chat( 
                current_user['id'],  # Pass the resolved user object
                message_content,  # Use the extracted message content
                session_id=title_chat_id 
            ) 
             
            # Save AI response 
            ai_message = await prisma.chat.create( 
                data={ 
                    'role': 'ASSISTANT', 
                    'content': response_data["response"], 
                    'titleChatId': title_chat_id 
                } 
            ) 
             
            # Update the TitleChat updatedAt timestamp 
            await prisma.titlechat.update( 
                where={'id': title_chat_id}, 
                data={'updatedAt': datetime.now()} 
            ) 
             
            return ChatResponse( 
                id=ai_message.id, 
                response=response_data["response"], 
                sessionId=title_chat_id, 
                sources=response_data.get("sources") 
            ) 
             
    except HTTPException: 
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e: 
        print(f"Error in chat endpoint: {str(e)}")  # Add logging
        raise HTTPException( 
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error processing chat: {str(e)}" 
        )

@router.post("/create", response_model=CreateSessionResponse)
async def create_chat_session(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new chat session"""
    from app.db.prisma_client import get_prisma
    
    try:
        async with get_prisma() as prisma:
            new_title_chat = await prisma.titlechat.create(
                data={
                    'title': 'New Chat',
                    'userId': current_user["id"]
                }
            )
            
            return CreateSessionResponse(
                id=new_title_chat.id,
                title=new_title_chat.title,
                createdAt=new_title_chat.createdAt,
                updatedAt=new_title_chat.updatedAt
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat session: {str(e)}"
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
                where={'id': session_id, 'userId': current_user["id"]}
            )

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )

            messages = await prisma.chat.find_many(
                where={'titleChatId': session_id},
                order=[{'createdAt': 'asc'}]
            )

            formatted_messages = []
            for msg in messages:
                formatted_messages.append(ChatHistoryItem(
                    id=msg.id,
                    role=msg.role.lower(),
                    content=msg.content,
                    createdAt=msg.createdAt
                ))
            
            return formatted_messages
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat session: {str(e)}"
        )
# Routes
@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get chat history for the current user with pagination"""
    from app.db.prisma_client import get_prisma

    try:
        async with get_prisma() as prisma:
            # Calculate offset for pagination
            offset = (page - 1) * limit
            
            # Get total count for pagination metadata
            total_count = await prisma.titlechat.count(
                where={'userId': current_user["id"]}
            )
            
            title_chats = await prisma.titlechat.find_many(
                where={'userId': current_user["id"]},
                include={
                    'chats': {
                        'order_by': [{'createdAt': 'desc'}],
                        'take': 1  # Get only the latest message for each chat
                    }
                },
                order=[{'updatedAt': 'desc'}],
                skip=offset,
                take=limit
            )
            
            formatted_sessions = []
            for title_chat in title_chats:
                last_message = "No messages yet"
                if title_chat.chats and len(title_chat.chats) > 0:
                    last_message = title_chat.chats[0].content
                    
                formatted_sessions.append(ChatSessionInfo(
                    id=title_chat.id,
                    title=title_chat.title,
                    lastMessage=last_message,
                    createdAt=title_chat.createdAt,
                    updatedAt=title_chat.updatedAt
                ))
            
            # Calculate pagination metadata
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
            has_next = page < total_pages
            has_prev = page > 1
            
            # Return response with pagination metadata
            return ChatHistoryResponse(
                data=formatted_sessions,
                pagination=PaginationInfo(
                    page=page,
                    limit=limit,
                    total=total_count,
                    total_pages=total_pages,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}"
        )

@router.put("/history/{session_id}", response_model=Dict[str, str])
async def update_chat_title(
    session_id: str,
    request: UpdateTitleRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update chat session title"""
    from app.db.prisma_client import get_prisma
    
    if not request.title or not isinstance(request.title, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required"
        )
    
    try:
        async with get_prisma() as prisma:
            # Verify the session belongs to the user and update title
            updated_count = await prisma.titlechat.update_many(
                where={
                    'id': session_id,
                    'userId': current_user["id"]
                },
                data={
                    'title': request.title.strip(),
                    'updatedAt': datetime.now()
                }
            )
            
            if updated_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            return {"message": "Chat title updated successfully"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating chat title: {str(e)}"
        )

@router.delete("/history/{session_id}", response_model=DeleteSessionResponse)
async def delete_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a chat session"""
    from app.db.prisma_client import get_prisma
    
    try:
        async with get_prisma() as prisma:
            # Verify the session belongs to the user
            title_chat = await prisma.titlechat.find_first(
                where={
                    'id': session_id,
                    'userId': current_user["id"]
                }
            )
            
            if not title_chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            
            # Delete the title chat (this will cascade delete all related chats)
            await prisma.titlechat.delete(
                where={'id': session_id}
            )
            
            return DeleteSessionResponse(
                message="Chat session deleted successfully"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting chat session: {str(e)}"
        )


@router.post("/", response_model=ChatResponse)
async def chat_legacy(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Legacy chat endpoint - redirects to new chat endpoint"""
    return await send_chat_message(request, current_user)

@router.put("/{session_id}", response_model=ChatResponse)
async def chat_session_legacy(
    session_id: str,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Legacy chat session endpoint - redirects to new chat endpoint"""
    request.sessionId = session_id
    return await send_chat_message(request, current_user)