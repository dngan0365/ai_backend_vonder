import json
import os
import csv
from dotenv import load_dotenv
import time as tm
from datetime import date, time, datetime
import nest_asyncio
from llama_index.agent.openai import OpenAIAgent

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core import PromptTemplate
from pydantic import BaseModel, Field

from app.chatbot.database.chat_history_service import get_recent_chat_history, format_chat_history, get_user_info
from app.chatbot.prompts.template import prompt_template
from app.chatbot.prompts.system import system_prompt
from app.chatbot.prompts.transform import transform_prompt
from app.chatbot.tools.tools import RetrieveDatabaseTool, RetrieveDataTool, RetrieveInternetTool
from llm_integration.openai_client import get_llmAgent, get_llmTransform

nest_asyncio.apply()

load_dotenv()
template = prompt_template()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class RetrieveModel(BaseModel):
    query: str = Field(..., description="The user's query in natural language.")

class ScheduleRetrieveModel(BaseModel):
    query: str = Field(..., description="The user's query in natural language.")
    filter_start_date: date = Field(
        ..., description="Start date of the schedule event in format YYYY-MM-DD"
    )
    filter_start_time: time = Field(
        ..., description="Start time of the schedule event in format HH:MM"
    )
    filter_end_date: date = Field(
        ..., description="End date of the schedule event in format YYYY-MM-DD"
    )
    filter_end_time: time = Field(
        ..., description="End time of the schedule event in format HH:MM"
    )



descriptionData = (
    "Use this tool to retrieve general tourism information in Vietnam such as attractions, popular destinations, cultural events,... "
    "recommended travel activities, and tips for travelers in Vietnam."
)

descriptionDatabase = (
    f"Use this tool to retrieve tours, locations and user-specific schedules, tour bookings, and planned events. "
    f"Helpful for checking what the user has planned. Today's date is {date.today().strftime('%Y-%m-%d')}, "
    f"and the current time is {datetime.now().strftime('%H:%M')} (used to reference current or upcoming plans)."
)

descriptionInternet = (
    "Use this tool to search the internet for travel-relate tips, weather, locations, tourist attractions,..."
)
# Create tools

async def get_answer(question: str, chat_id: str, user_id: str) -> str:
    """
    Hàm lấy câu trả lời cho một câu hỏi (không dùng stream)
    
    Args:
        question (str): Câu hỏi của người dùng
        chat_id (str): ID phiên chat
        user_id (str): ID người dùng
        
    Returns:
        str: Câu trả lời hoàn chỉnh từ agent
    """
    
    chat = get_llmAgent()

    retrieveDataTool = FunctionTool.from_defaults(
        fn=RetrieveDataTool,
        name="attraction_tourisms_and_events_in_vietnam",
        description=descriptionData,
        fn_schema=RetrieveModel,
    )
    retrieveDatabaseTool = FunctionTool.from_defaults(
        fn=RetrieveDatabaseTool,
        name="events_tours",
        description=descriptionDatabase,
        fn_schema=RetrieveModel,
    )

    retrieveInternetTool = FunctionTool.from_defaults(
        fn=RetrieveInternetTool,
        name="internet_search",
        description=descriptionInternet,
        fn_schema=RetrieveModel,
    )

    tools = [retrieveDataTool, retrieveDatabaseTool, retrieveInternetTool]
    print("Tools initialized:", tools)
    # Initialize the OpenAIAgent with the tools and LLM
    print("Initializing OpenAIAgent with tools and LLM")
    # Ensure the system prompt is set
    agent = OpenAIAgent.from_tools(
        tools,
        llm=chat,
        verbose=True,
        system_prompt=system_prompt(),
        api_key=OPENAI_API_KEY,
    )
    print("OpenAIAgent initialized successfully")
    # Ensure the agent is ready
    # Prompt to generate similar queries
    query_gen_prompt = PromptTemplate(question)
    llm = get_llmTransform()

    # Lấy lịch sử chat gần đây
    print("Fetching recent chat history and user info")
    # Lấy lịch sử chat và thông tin người dùng
    history = await get_recent_chat_history(chat_id)
    
    print("Chat history fetched:", history)
    chat_history = format_chat_history(history)
    print("Formatted chat history:", chat_history)
    
    print("Fetching user info for user_id:", user_id)
    # Lấy thông tin người dùng
    user_info = await get_user_info(user_id)
    
    def generate_queries(query: str, llm, num_queries: int = 4):
        query_gen_prompt = PromptTemplate(transform_prompt())
        response = llm.predict(
            query_gen_prompt, num_queries=num_queries, query=query
        )
        # assume LLM proper put each query on a newline
        queries = response.split("\n")
        return queries

    # Tạo các câu hỏi tương tự từ câu hỏi gốc
    print("Generating similar queries for the question:", question)
    queries = generate_queries(question, llm)
    
    print("Similar queries generated:", queries)
    # Kiểm tra nếu không có câu hỏi tương tự nào được tạo ra

    # Tạo prompt chính cho agent
    prompt = PromptTemplate(
        template=template,
        function_mappings={
            "formatted_history": lambda: str(chat_history),
            "formatted_user": lambda: str(user_info),
            "question": lambda: question,
            "similar_question": lambda: "\n".join(queries),
        },
    )

    rendered_prompt = prompt.template.format(
        formatted_history=prompt.function_mappings["formatted_history"](),
        formatted_user=prompt.function_mappings["formatted_user"](),
        question=prompt.function_mappings["question"](),
        similar_question=prompt.function_mappings["similar_question"](),
    )
    print("Rendered prompt:", rendered_prompt)
    # Gọi agent để lấy câu trả lời
    print("Calling agent to get the response for the question")
    response = await agent.achat(rendered_prompt)

    return response.response

    
    
