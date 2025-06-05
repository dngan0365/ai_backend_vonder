from llama_index.llms.openai import OpenAI
import os 
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment
api_key = os.getenv("OPENAI_API_KEY")

llmTitle = OpenAI(        
        temperature=0.2,
        model="gpt-4o-mini",
        api_key=api_key)

llmAgent = OpenAI(
        temperature=0.1,
        model="gpt-4o-mini",
        api_key=api_key)

llmRetriever = OpenAI(
        temperature=0,
        model="gpt-4o-mini",
        api_key=api_key)

llmTransform = OpenAI(
        temperature=0.2,
        model="gpt-4o-mini",
        api_key=api_key)


def get_llmTitle():
    return llmTitle

def get_llmAgent():
    return llmAgent

def get_llmRetriever():
    return llmRetriever

def get_llmTransform():
    return llmTransform