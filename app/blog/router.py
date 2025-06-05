from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

class BlogPost(BaseModel):
    title: str
    content: str

@app.post("/review")
async def review_blog(post: BlogPost):
    prompt = f"""
You are an AI blog moderator. Review the following blog post based on these criteria:

1. No offensive or harmful language.
2. Free of grammar and spelling errors.
3. Matches the topic: Technology, AI, or Software Development.
4. Appears to be human-written and original.
5. At least 500 words and properly formatted.

Respond in this JSON format:
{{
  "passed": true or false,
  "issues": ["List specific issues"],
  "suggestions": ["List actionable suggestions"]
}}

Title: {post.title}

Content:
{post.content}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response['choices'][0]['message']['content']
        print(f"GPT Response: {content}")
        return eval(content)  # Assumes GPT returns a valid Python-style dict string
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
