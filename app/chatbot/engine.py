from typing import List, Dict, Any, Optional
import json
from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.core.node_parser import SentenceSplitter


from app.config import settings
from app.db.prisma_client import get_prisma


class ChatbotEngine:
    """Chatbot engine using LlamaIndex"""
    
    def __init__(self):
        # Initialize LLM
        self.llm = OpenAI(
            model="gpt-3.5-turbo", 
            api_key=settings.OPENAI_API_KEY
        )
        
        # Initialize embedding model
        self.embed_model = OpenAIEmbedding(
            model="text-embedding-ada-002",
            api_key=settings.OPENAI_API_KEY
        )
        
        # Set up sentence splitter (node parser)
        Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

        # Set global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.num_output = 512
        Settings.context_window = 3900

        # Create memory
        self.memory = ChatSummaryMemoryBuffer.from_defaults(token_limit=3900)
    
    async def load_database_as_documents(self) -> List[Document]:
        """Load database records as documents for indexing"""
        documents = []
        
        async with get_prisma() as prisma:
            # Load locations
            locations = await prisma.location.find_many(
                include={
                    'blogs': True,
                    'events': {
                        'include': {
                            'event': True
                        }
                    },
                    'trips': True
                }
            )
            
            for location in locations:
                # Convert to dictionary and serialize to JSON
                loc_dict = location.dict()
                document = Document(
                    text=json.dumps(loc_dict, default=str),
                    metadata={
                        "type": "location",
                        "id": location.id,
                        "name": location.name,
                        "category": location.category,
                        "province": location.province
                    }
                )
                documents.append(document)
            
            # Load blogs
            blogs = await prisma.blog.find_many(
                include={
                    'author': True,
                    'locations': True,
                    'comments': {
                        'include': {
                            'user': True,
                            'replies': {
                                'include': {
                                    'user': True
                                }
                            }
                        }
                    }
                }
            )
            
            for blog in blogs:
                blog_dict = blog.dict()
                document = Document(
                    text=json.dumps(blog_dict, default=str),
                    metadata={
                        "type": "blog",
                        "id": blog.id,
                        "title": blog.title,
                        "author": blog.author.name,
                        "category": blog.category
                    }
                )
                documents.append(document)
            
            # Load events
            events = await prisma.event.find_many(
                include={
                    'locations': {
                        'include': {
                            'location': True
                        }
                    }
                }
            )
            
            for event in events:
                event_dict = event.dict()
                document = Document(
                    text=json.dumps(event_dict, default=str),
                    metadata={
                        "type": "event",
                        "id": event.id,
                        "name": event.name
                    }
                )
                documents.append(document)
                
        return documents
    
    async def initialize_index(self):
        """Initialize or update the vector index"""
        documents = await self.load_database_as_documents()
        self.index = VectorStoreIndex.from_documents(
            documents
        )
        
        # Create query engine
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=5,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)]
        )
        
        # Create chat engine
        self.chat_engine = self.index.as_chat_engine(
            chat_memory=self.memory,
            similarity_top_k=5,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)]
        )
    
    async def chat(self, user_id: str, message: str) -> Dict[Any, Any]:
        """Process user message and generate response"""
        # Check if index is initialized
        if not hasattr(self, 'chat_engine'):
            await self.initialize_index()
            
        # Query the chat engine
        response = self.chat_engine.chat(message)
        
        # Save the chat to the database
        async with get_prisma() as prisma:
            # Check if there's an existing chat session for this user
            title_chat = await prisma.titlechat.find_first(
                where={
                    'userId': user_id
                },
                order=[
                    {
                    'createdAt': 'desc'
                }
                ]
            )
            
            # If no session exists, create one
            if not title_chat:
                title = f"Chat session {message[:20]}..."
                title_chat = await prisma.titlechat.create(
                    data={
                        'title': title,
                        'userId': user_id,
                        'chats': {
                            'create': [
                                {
                                    'role': 'USER',
                                    'content': message
                                },
                                {
                                    'role': 'ASSISTANT',
                                    'content': response.response
                                }
                            ]
                        }
                    }
                )
            else:
                # Add to existing chat session
                await prisma.chat.create_many(
                    data=[
                        {
                            'role': 'USER',
                            'content': message,
                            'titleChatId': title_chat.id
                        },
                        {
                            'role': 'ASSISTANT',
                            'content': response.response,
                            'titleChatId': title_chat.id
                        }
                    ]
                )
                
        return {
            "response": response.response,
            "sources": [src.metadata for src in response.source_nodes] if hasattr(response, 'source_nodes') else []
        }
    
    async def refresh_index(self):
        """Refresh the index with latest database data"""
        await self.initialize_index()
        return {"status": "success", "message": "Index refreshed successfully"}