import asyncio
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import logging



# Import your existing get_answer function
from app.chatbot.service import get_answer  # Update this import path

logger = logging.getLogger(__name__)

class ChatbotEngine:
    """
    ChatbotEngine class that wraps your existing get_answer function
    and provides the interface needed for the FastAPI router
    """
    
    def __init__(self):
        """Initialize the ChatbotEngine"""
        self.active_sessions = {}
        logger.info("ChatbotEngine initialized")
    
    async def chat(
        self, 
        user_id: str, 
        message: str, 
        session_id: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response
        
        Args:
            user_id (str): The user ID
            message (str): The user's message
            session_id (Optional[str]): Session ID for the chat
            stream (bool): Whether to stream the response (not implemented yet)
            
        Returns:
            Dict[str, Any]: Response containing the answer and metadata
        """
        try:
            print(f"Processing chat message from user {user_id} in session {session_id}")
            # Call your existing get_answer function
            response = await get_answer(
                question=message,
                chat_id=session_id,
                user_id=user_id
            )
            
            # Track session activity
            self.active_sessions[session_id] = {
                'user_id': user_id,
                'last_activity': datetime.now(),
                'message_count': self.active_sessions.get(session_id, {}).get('message_count', 0) + 1
            }
            
            # Return structured response
            return {
                'response': response,
                'session_id': session_id,
                'sources': self._extract_sources(response),  # Optional: extract source information
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'user_id': user_id,
                    'session_id': session_id,
                    'processing_time': None  # Could be added if you track timing
                }
            }
            
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}")
            raise Exception(f"Failed to process chat message: {str(e)}")
    
    async def chat_stream(
        self, 
        user_id: str, 
        message: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response (placeholder for future streaming implementation)
        
        Args:
            user_id (str): The user ID
            message (str): The user's message
            session_id (Optional[str]): Session ID for the chat
            
        Yields:
            Dict[str, Any]: Streaming response chunks
        """
        try:
            # For now, just yield the complete response
            # You can modify this later to implement true streaming
            response = await self.chat(user_id, message, session_id)
            
            # Simulate streaming by yielding chunks
            words = response['response'].split()
            chunk_size = 5  # Words per chunk
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                yield {
                    'chunk': chunk,
                    'is_complete': i + chunk_size >= len(words),
                    'session_id': response['session_id'],
                    'timestamp': datetime.now().isoformat()
                }
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield {
                'error': str(e),
                'is_complete': True,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific session
        
        Args:
            session_id (str): The session ID
            
        Returns:
            Optional[Dict[str, Any]]: Session information or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get active sessions, optionally filtered by user
        
        Args:
            user_id (Optional[str]): Filter by user ID
            
        Returns:
            Dict[str, Any]: Active sessions information
        """
        if user_id:
            return {
                session_id: info 
                for session_id, info in self.active_sessions.items() 
                if info['user_id'] == user_id
            }
        return self.active_sessions.copy()
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """
        Clean up inactive sessions older than max_age_hours
        
        Args:
            max_age_hours (int): Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        sessions_to_remove = [
            session_id for session_id, info in self.active_sessions.items()
            if info['last_activity'] < cutoff_time
        ]
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            
        logger.info(f"Cleaned up {len(sessions_to_remove)} inactive sessions")
    
    def _extract_sources(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract source information from the response
        
        Args:
            response (str): The response text
            
        Returns:
            Optional[List[Dict[str, Any]]]: Extracted sources
        """
        # Placeholder implementation
        # You might want to parse the response to extract source citations
        sources = []
        
        # Example: if your response contains source markers
        if "Source:" in response or "Sources:" in response or "sourece:" in response or "source:" in response or "sources:" in response:
            # Split by source markers and extract source information
            parts = response.split("Source:")
            for part in parts[1:]:
                source_info = part.strip().split("\n")[0]  # Get the first line as source
                sources.append({'source': source_info})
        
        return sources if sources else None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the chatbot engine
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Test basic functionality
            test_response = await self.chat(
                user_id="health_check",
                message="test",
                session_id="health_check_session"
            )
            
            return {
                'status': 'healthy',
                'active_sessions': len(self.active_sessions),
                'timestamp': datetime.now().isoformat(),
                'test_response_received': bool(test_response.get('response'))
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Async context manager version (optional)
class AsyncChatbotEngine(ChatbotEngine):
    """
    Async context manager version of ChatbotEngine
    """
    
    async def __aenter__(self):
        """Async context manager entry"""
        logger.info("Entering ChatbotEngine context")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        logger.info("Exiting ChatbotEngine context")
        # Cleanup resources if needed
        self.cleanup_inactive_sessions()


# Factory function for easy instantiation
def create_chatbot_engine() -> ChatbotEngine:
    """
    Factory function to create a ChatbotEngine instance
    
    Returns:
        ChatbotEngine: New chatbot engine instance
    """
    return ChatbotEngine()


# Example usage
if __name__ == "__main__":
    async def test_engine():
        engine = ChatbotEngine()
        
        # Test basic chat
        response = await engine.chat(
            user_id="test_user",
            message="Hello, how are you?",
            session_id="test_session"
        )
        
        print("Response:", response)
        
        # Test health check
        health = await engine.health_check()
        print("Health:", health)
        
        # Test streaming (placeholder)
        print("Streaming test:")
        async for chunk in engine.chat_stream("test_user", "Tell me about Vietnam"):
            print("Chunk:", chunk)
    
    # Run test
    asyncio.run(test_engine())