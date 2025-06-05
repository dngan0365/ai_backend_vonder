from datetime import date, time
import json
from llama_index.tools.tavily_research import TavilyToolSpec
from llama_index.core.tools import FunctionTool
from llama_index.core.vector_stores import (
    VectorStoreInfo,
    MetadataInfo,
    MetadataFilter,
    MetadataFilters,
    FilterCondition,
    FilterOperator,
)
from typing import List, Dict, Any, Optional
from datetime import datetime, date, time
from pydantic import BaseModel
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.core.retrievers import VectorIndexAutoRetriever
from llama_index.core import Settings
import weaviate
from llama_index.core.agent import FunctionCallingAgent
from app.db.prisma_client import prisma  # Import your prisma client


from fastapi import Depends
from llama_index.core import Settings
import csv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from IPython.display import Markdown, display
from fastapi import Depends
from typing import List, Tuple, Any
from pydantic import BaseModel, Field
import datetime
import yaml
import os
# core/ai/tools/tools.py
from llm_integration.embedding_client import get_embed_model
from llm_integration.weaviate_client import get_weaviate_client
from llm_integration.openai_client import get_llmRetriever
from llama_index.core.response.notebook_utils import display_source_node
from app.db.prisma_client import prisma

Settings.embed_model = get_embed_model()

# hardcode top k for now
top_k = 4

client = get_weaviate_client()

# define vector store info describing schema of vector store
vector_store_info = VectorStoreInfo(
    content_info="Chứa những thông tin về các địa điểm, tips, các địa điểm ở Việt Nam",
    metadata_info=[
        MetadataInfo(
            name="title",
            type="str",
            description=(
                "Tiêu đề của tài liệu chứa thông tin"
            ),
        ),
        MetadataInfo(
            name="document_title",
            type="str",
            description=(
                "Chủ đề của thông tin"
            ),
        ),
        MetadataInfo(
            name="date",
            type="str",
            description=(
                "Ngày tháng năm thông tin được cập nhật"
            ),
        ),
        MetadataInfo(
            name="source",
            type="str",
            description=(
                "Nguồn thông tin có thể là một đường dẫn hoặc tên trang web"
            ),
        ),
    ],
)


def RetrieveDataTool(query: str = None, embed_model = Depends(get_embed_model)) :
    """
    Hàm truy vấn thông tin về các địa điểm du lịch ở Việt Nam từ cơ sở dữ liệu vector store Weaviate.
    """
    # Define the vector store

    vector_store = WeaviateVectorStore(
        weaviate_client=client, index_name="VietnamTourism", text_key="content"
    )

    loaded_index = VectorStoreIndex.from_vector_store(vector_store)
    
    """Auto retrieval function.

    Performs auto-retrieval from a vector database, and then applies a set of filters.

    """
    query = query or "Query"

    llm = get_llmRetriever()
    
    retriever = VectorIndexAutoRetriever(
        loaded_index,
        vector_store_info=vector_store_info,
        llm = llm,
        vector_store_query_mode="hybrid", 
        alpha=0.4,
        similarity_top_k = top_k, 
        enable_reranking=True,
    )

    response = retriever.retrieve(query)
        
    # Format response as a string with text, source, and date
    formatted_strings = []
    
    for i, item in enumerate(response):
        text = item.text
        source = (item.metadata.get("source") or item.metadata.get("src_url") or "no source")# Lấy source từ metadata
        date = item.metadata.get("date", "no date")       # Lấy date từ metadata
        
        # Định dạng chuỗi
        formatted_string = f"{i + 1}. {text} (Source: {source}, Updated date: {date})"
        formatted_strings.append(formatted_string)

    # Kết quả là danh sách các chuỗi định dạng
    result = "\n".join(formatted_strings)
    
    # write_to_next_empty_row(["RetrieveLifeBloodTool", result])
    return result


def RetrieveInternetTool(query: str) :
    """
    Tìm kiếm thông tin trên internet
    """
    tavily_tool = TavilyToolSpec(
        api_key=os.environ["TAVILY_API_KEY"],
    )
    agent = FunctionCallingAgent.from_tools(
        tavily_tool.to_tool_list(),
        llm=OpenAI(model="gpt-4o-mini", temperature=0.1, api_key=os.environ["OPENAI_API_KEY"], verbose=True),
    )
    return agent.chat(query)



class DatabaseQuery(BaseModel):
    entity_type: str
    filters: Dict[str, Any] = {}
    user_id: Optional[str] = None
    limit: int = 10


tools = [
    {
        "type": "function",
        "function": {
            "name": "RetrieveDatabaseTool",
            "description": "Truy vấn cơ sở dữ liệu để lấy thông tin về trips, events, tours, agencies, locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Câu hỏi người dùng, ví dụ 'Sự kiện ở Hà Nội tháng 7'"
                    },
                    "filter_start_date": {"type": "string", "format": "date", "description": "Ngày bắt đầu lọc"},
                    "filter_end_date": {"type": "string", "format": "date", "description": "Ngày kết thúc lọc"},
                    "filter_start_time": {"type": "string", "format": "time"},
                    "filter_end_time": {"type": "string", "format": "time"},
                    "user_id": {"type": "string"},
                    "entity_type": {
                        "type": "string",
                        "enum": ["trip", "event", "tour", "agency", "location", "general"]
                    },
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        }
    }
]

async def RetrieveDatabaseTool(
    query: str,
    filter_start_date: Optional[date] = None,
    filter_start_time: Optional[time] = None,
    filter_end_date: Optional[date] = None,
    filter_end_time: Optional[time] = None,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Truy vấn cơ sở dữ liệu để lấy thông tin về trips, events, tours, agencies, locations, etc.
    
    Args:
        query: Câu truy vấn của người dùng
        filter_start_date: Ngày bắt đầu để lọc
        filter_start_time: Thời gian bắt đầu để lọc
        filter_end_date: Ngày kết thúc để lọc
        filter_end_time: Thời gian kết thúc để lọc
        user_id: ID của người dùng
        entity_type: Loại entity cần truy vấn (trip, event, tour, agency, location)
        limit: Số lượng kết quả tối đa
    
    Returns:
        List[Dict]: Danh sách các kết quả truy vấn
    """
    
    # Parse query to determine intent and entity type
    parsed_intent = parse_query_intent(query)
    
    if not entity_type:
        entity_type = parsed_intent.get('entity_type', 'trip')
    
    # Build datetime filters
    datetime_filters = build_datetime_filters(
        filter_start_date, filter_start_time,
        filter_end_date, filter_end_time
    )
    
    try:
        if entity_type.lower() == 'trip':
            return await retrieve_trips(query, user_id, datetime_filters, limit)
        elif entity_type.lower() == 'event':
            return await retrieve_events(query, user_id, datetime_filters, limit)
        elif entity_type.lower() == 'tour':
            return await retrieve_tours(query, datetime_filters, limit)
        elif entity_type.lower() == 'agency':
            return await retrieve_agencies(query, limit)
        elif entity_type.lower() == 'location':
            return await retrieve_locations(query, limit)
        else:
            return await retrieve_general(query, user_id, datetime_filters, limit)
            
    except Exception as e:
        return [{"error": f"Database query failed: {str(e)}"}]

def parse_query_intent(query: str) -> Dict[str, Any]:
    """
    Phân tích câu truy vấn để xác định intent và entity type
    """
    query_lower = query.lower()
    
    # Keywords mapping
    keywords_map = {
        'trip': ['chuyến đi', 'trip', 'travel', 'du lịch', 'lịch trình'],
        'event': ['sự kiện', 'event', 'hoạt động', 'lễ hội'],
        'tour': ['tour', 'chuyến tham quan', 'gói du lịch'],
        'agency': ['công ty', 'agency', 'đại lý', 'nhà cung cấp'],
        'location': ['địa điểm', 'location', 'nơi', 'vị trí', 'thành phố', 'tỉnh']
    }
    
    for entity_type, keywords in keywords_map.items():
        if any(keyword in query_lower for keyword in keywords):
            return {'entity_type': entity_type}
    
    return {'entity_type': 'general'}

def build_datetime_filters(start_date, start_time, end_date, end_time):
    """
    Xây dựng bộ lọc datetime
    """
    filters = {}
    
    if start_date:
        start_datetime = datetime.combine(start_date, start_time or time.min)
        filters['start_datetime'] = start_datetime
    
    if end_date:
        end_datetime = datetime.combine(end_date, end_time or time.max)
        filters['end_datetime'] = end_datetime
    
    return filters

async def retrieve_trips(query: str, user_id: Optional[str], datetime_filters: Dict, limit: int) -> List[Dict]:
    """
    Truy vấn thông tin về trips sử dụng Prisma
    """
    try:
        # Build where conditions
        where_conditions = {}
        
        # Add user filter through trip participants
        if user_id:
            where_conditions['participants'] = {
                'some': {
                    'userId': user_id
                }
            }
        
        # Add datetime filters
        if 'start_datetime' in datetime_filters:
            where_conditions['startDate'] = {
                'gte': datetime_filters['start_datetime']
            }
        
        if 'end_datetime' in datetime_filters:
            where_conditions['endDate'] = {
                'lte': datetime_filters['end_datetime']
            }
        
        # Add text search
        if query:
            where_conditions['OR'] = [
                {'name': {'contains': query, 'mode': 'insensitive'}},
                {'description': {'contains': query, 'mode': 'insensitive'}},
                {'location': {
                    'name': {'contains': query, 'mode': 'insensitive'}
                }}
            ]
        
        # Execute Prisma query
        trips = await prisma.trip.find_many(
            where=where_conditions,
            include={
                'location': True,
                'participants': True
            },
            order=[{'createdAt': 'desc'}],
            take=limit
        )
        
        return format_trip_results(trips)
        
    except Exception as e:
        print(f"Error retrieving trips: {e}")
        return []

async def retrieve_events(query: str, user_id: Optional[str], datetime_filters: Dict, limit: int) -> List[Dict]:
    """
    Truy vấn thông tin về events sử dụng Prisma
    """
    try:
        where_conditions = {}
        
        # Add user filter through saved events
        if user_id:
            where_conditions['saveEvents'] = {
                'some': {
                    'userId': user_id
                }
            }
        
        # Add datetime filters
        if 'start_datetime' in datetime_filters:
            where_conditions['startDate'] = {
                'gte': datetime_filters['start_datetime']
            }
        
        if 'end_datetime' in datetime_filters:
            where_conditions['endDate'] = {
                'lte': datetime_filters['end_datetime']
            }
        
        # Add text search
        if query:
            where_conditions['OR'] = [
                {'name': {'contains': query, 'mode': 'insensitive'}},
                {'description': {'contains': query, 'mode': 'insensitive'}}
            ]
        
        # Execute Prisma query
        events = await prisma.event.find_many(
            where=where_conditions,
            include={
                'eventLocation': {
                    'include': {
                        'location': True
                    }
                }
            },
            order=[{'createdAt': 'desc'}],
            take=limit
        )
        
        return format_event_results(events)
        
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []

async def retrieve_tours(query: str, datetime_filters: Dict, limit: int) -> List[Dict]:
    """
    Truy vấn thông tin về tours sử dụng Prisma
    """
    try:
        where_conditions = {}
        
        # Add text search
        if query:
            where_conditions['OR'] = [
                {'title': {'contains': query, 'mode': 'insensitive'}},
                {'description': {'contains': query, 'mode': 'insensitive'}},
                {'location': {
                    'name': {'contains': query, 'mode': 'insensitive'}
                }}
            ]
        
        # Execute Prisma query
        tours = await prisma.tour.find_many(
            where=where_conditions,
            include={
                'agency': True,
                'location': True
            },
             order=[{'createdAt': 'desc'}],
            take=limit
        )
        
        return format_tour_results(tours)
        
    except Exception as e:
        print(f"Error retrieving tours: {e}")
        return []

async def retrieve_agencies(query: str, limit: int) -> List[Dict]:
    """
    Truy vấn thông tin về agencies sử dụng Prisma
    """
    try:
        where_conditions = {}
        
        if query:
            where_conditions['OR'] = [
                {'name': {'contains': query, 'mode': 'insensitive'}},
                {'description': {'contains': query, 'mode': 'insensitive'}}
            ]
        
        # Execute Prisma query
        agencies = await prisma.agency.find_many(
            where=where_conditions,
            include={
                'tours': True
            },
            order=[
                {'verified': 'desc'},
                {'createdAt': 'desc'}
            ],
            take=limit
        )
        
        return format_agency_results(agencies)
        
    except Exception as e:
        print(f"Error retrieving agencies: {e}")
        return []

async def retrieve_locations(query: str, limit: int) -> List[Dict]:
    """
    Truy vấn thông tin về locations sử dụng Prisma
    """
    try:
        where_conditions = {}
        
        if query:
            where_conditions['OR'] = [
                {'name': {'contains': query, 'mode': 'insensitive'}},
                {'province': {'contains': query, 'mode': 'insensitive'}},
                {'district': {'contains': query, 'mode': 'insensitive'}}
            ]
        
        # Execute Prisma query
        locations = await prisma.location.find_many(
            where=where_conditions,
            include={
                'trips': True,
                'tours': True
            },
            take=limit
        )
        
        return format_location_results(locations)
        
    except Exception as e:
        print(f"Error retrieving locations: {e}")
        return []

async def retrieve_general(query: str, user_id: Optional[str], datetime_filters: Dict, limit: int) -> List[Dict]:
    """
    Truy vấn tổng hợp từ nhiều bảng sử dụng Prisma
    """
    results = []
    per_type_limit = max(1, limit // 3)
    
    try:
        # Search in trips
        trip_results = await retrieve_trips(query, user_id, datetime_filters, per_type_limit)
        results.extend([{**item, 'type': 'trip'} for item in trip_results])
        
        # Search in events
        event_results = await retrieve_events(query, user_id, datetime_filters, per_type_limit)
        results.extend([{**item, 'type': 'event'} for item in event_results])
        
        # Search in tours
        tour_results = await retrieve_tours(query, datetime_filters, per_type_limit)
        results.extend([{**item, 'type': 'tour'} for item in tour_results])
        
        return results[:limit]
        
    except Exception as e:
        print(f"Error in general retrieval: {e}")
        return []

def format_trip_results(trips) -> List[Dict]:
    """
    Format trip results for chatbot response
    """
    formatted = []
    for trip in trips:
        formatted.append({
            'id': trip.id,
            'name': trip.name,
            'description': trip.description,
            'start_date': trip.startDate.isoformat() if trip.startDate else None,
            'end_date': trip.endDate.isoformat() if trip.endDate else None,
            'location': trip.location.name if trip.location else None,
            'province': trip.location.province if trip.location else None,
            'district': trip.location.district if trip.location else None,
            'hotel_name': trip.hotelName,
            'hotel_address': trip.hotelAddress,
            'participants_count': len(trip.tripParticipants) if trip.tripParticipants else 0,
            'type': 'trip'
        })
    return formatted

def format_event_results(events) -> List[Dict]:
    """
    Format event results for chatbot response
    """
    formatted = []
    for event in events:
        # Get all location names
        locations = []
        if event.eventLocations:
            locations = [el.location.name for el in event.eventLocations if el.location]
        
        formatted.append({
            'id': event.id,
            'name': event.name,
            'description': event.description,
            'start_date': event.startDate.isoformat() if event.startDate else None,
            'end_date': event.endDate.isoformat() if event.endDate else None,
            'cover_image': event.coverImage,
            'locations': ', '.join(locations),
            'type': 'event'
        })
    return formatted

def format_tour_results(tours) -> List[Dict]:
    """
    Format tour results for chatbot response
    """
    formatted = []
    for tour in tours:
        # Parse images if it's a JSON string
        images = []
        if tour.images:
            try:
                if isinstance(tour.images, str):
                    images = json.loads(tour.images)
                elif isinstance(tour.images, list):
                    images = tour.images
            except:
                images = []
                
        formatted.append({
            'id': tour.id,
            'title': tour.title,
            'description': tour.description,
            'price': float(tour.price) if tour.price else None,
            'duration': tour.duration,
            'max_capacity': tour.maxCapacity,
            'agency_name': tour.agency.name if tour.agency else None,
            'location': tour.location.name if tour.location else None,
            'province': tour.location.province if tour.location else None,
            'category': tour.category,
            'images': images,
            'type': 'tour'
        })
    return formatted

def format_agency_results(agencies) -> List[Dict]:
    """
    Format agency results for chatbot response
    """
    formatted = []
    for agency in agencies:
        formatted.append({
            'id': agency.id,
            'name': agency.name,
            'email': agency.email,
            'description': agency.description,
            'website': agency.website,
            'phone_number': agency.phoneNumber,
            'address': agency.address,
            'verified': agency.verified,
            'total_tours': len(agency.tours) if agency.tours else 0,
            'type': 'agency'
        })
    return formatted

def format_location_results(locations) -> List[Dict]:
    """
    Format location results for chatbot response
    """
    formatted = []
    for location in locations:
        formatted.append({
            'id': location.id,
            'name': location.name,
            'province': location.province,
            'district': location.district,
            'total_trips': len(location.trips) if location.trips else 0,
            'total_tours': len(location.tours) if location.tours else 0,
            'type': 'location'
        })
    return formatted

# Example usage and test cases
async def test_database_tool():
    """
    Test cases for the database retrieval tool
    """
    test_cases = [
        {
            'query': 'chuyến đi đến Hà Nội',
            'expected_entity': 'trip'
        },
        {
            'query': 'sự kiện lễ hội',
            'expected_entity': 'event'
        },
        {
            'query': 'tour du lịch Sapa',
            'expected_entity': 'tour'
        },
        {
            'query': 'công ty du lịch ở TPHCM',
            'expected_entity': 'agency'
        }
    ]
    
    for test in test_cases:
        intent = parse_query_intent(test['query'])
        print(f"Query: {test['query']}")
        print(f"Detected entity: {intent.get('entity_type')}")
        print(f"Expected: {test['expected_entity']}")
        print("---")
        
        # Test actual retrieval
        try:
            results = await RetrieveDatabaseTool(
                query=test['query'],
                entity_type=intent.get('entity_type'),
                limit=5
            )
            print(f"Results count: {len(results)}")
            print("Sample result:", results[0] if results else "No results")
            print("---")
        except Exception as e:
            print(f"Error testing {test['query']}: {e}")
            print("---")

