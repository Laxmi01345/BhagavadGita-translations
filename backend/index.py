from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
import google.generativeai as genai
from dotenv import load_dotenv
import os
from mongodbconfig import chapters_collection, verses_collection

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://bhagavadgita-seven.vercel.app",
        "https://bhagavadgitafrontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

def configuration_gemini():
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-1.5-pro')

@app.get("/")
async def root():
    return {"message": "Bhagavad Gita API is running"}

@app.get("/generate/verse/{chapter}/{verse}")
async def generate_single_verse(chapter: int, verse: int):
    try:
        model = configuration_gemini()
        response = await generate_verse(model, chapter, verse)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate/verses/{chapter}/{start}/{end}")
async def generate_multiple_verses(chapter: int, start: int, end: int):
    try:
        model = configuration_gemini()
        response = await generate_verses_range(model, chapter, start, end)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chapters")
async def get_chapters():
    try:
        chapters = list(chapters_collection.find({}, {'_id': 0}))
        return chapters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verses/{chapter}")
async def get_verses(chapter: int):
    try:
        verses = list(verses_collection.find({"chapter_id": chapter}, {'_id': 0}))
        return verses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



