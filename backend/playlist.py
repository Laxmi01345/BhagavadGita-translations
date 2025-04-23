from googleapiclient.discovery import build
import json
from dotenv import load_dotenv
import os
import google.generativeai as genai
from mongodbconfig import chapters_collection
from mongodbconfig import verses_collection

load_dotenv()

def configuration_gemini():
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key = GEMINI_API_KEY)
    
    model = genai.GenerativeModel('gemini-1.5-pro')
    return model

async def generate_verse(model, chapter_number):
    prompt = f"""
Generate the  verse 12 of Bhagavad Gita Chapter {chapter_number} in strict JSON format.

Requirements:
- Only output a JSON object, no markdown, code blocks, or explanations.
- The JSON must be valid and parseable.
- Do not include any extra text, headers, or formatting.

Each verse must contain:

- "verse_id" (string)
- "sanskrit_text" (list of strings)
- "transliteration" (list of strings)
- "word_by_word" (dictionary of Sanskrit words to English meanings)
- "translation" (string)
- "interpretations" (dictionary with keys: 'Historical', 'Symbolic', 'Literal', 'Spiritual', 'Ironic', 'Psychological')

The output should match this structure exactly (with actual verse-specific values):

{{
  
  "verse_id": "",
  "sanskrit_text": [],
  "transliteration": [],
  "word_by_word": {{}},
  "translation": "",
  "interpretations": {{
    "Historical": "",
    "Symbolic": "",
    "Literal": "",
    "Spiritual": "",
    "Ironic": "",
    "Psychological": ""
  }}
}}
"""


    try:
        response = model.generate_content(prompt)
        data = response.text.strip()
        if data.startswith("```json"):
            data = data[len("```json"):].strip()
        elif data.startswith("```"):
          data = data[len("```"):].strip()
        if data.endswith("```"):
         data = data[:-3].strip()
        if data.lower().startswith("json"):
             data = data[4:].strip()
        parsed_data = json.loads(data)
        print(parsed_data)
        
        
    
        isChapterExist = chapters_collection.find_one({"chapter_id": chapter_number})

        if isChapterExist:
            try :
                verse_data = json.loads(data)
                verse_data["chapter_id"] = chapter_number
                verses_collection.insert_one(verse_data)
                print(f"Stored verse for chapter {chapter_number}")
            
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


async def get_playlist_videos(api_key, playlist_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    videos=[]   
    chapter_cnt=1
    next_page_token = None 
    while True:
        playlist_request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token 

        )
        playlist_response = playlist_request.execute()

        for item in playlist_response['items']:
            video_data = {
                'chapter_id': chapter_cnt,
                'title': item['snippet']['title'],
                'video_id': item['snippet']['resourceId']['videoId'],
                'url': f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"
            }
            print(  "chapter_id : ",video_data["chapter_id"])
            existing_chapter = chapters_collection.find_one({"chapter_id": video_data["chapter_id"]})
            if existing_chapter:
                    chapters_collection.update_one(
                        {'chapter_id': video_data['chapter_id']},
                        {'$set': {'video_url': video_data['url']}}
                    )
                    print(f"Updated chapter {video_data['chapter_id']} with video URL")
                
            videos.append({
                    'title': item['snippet']['title'],
                    'chapter_id': video_data['chapter_id'],
                    'url': video_data['url']
            })
            chapter_cnt+=1
                
        
        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break
    
    print(json.dumps(videos, indent=2))       

API_KEY = os.getenv('YOUTUBE_API_KEY')
PLAYLIST_ID = os.getenv('YOUTUBE_PLAYLIST_ID')

chapter_titles = {
    1: "Arjuna Vishada Yoga (The Yoga of Arjuna's Grief)",
    2: "Sankhya Yoga (The Yoga of Knowledge)",
    3: "Karma Yoga (The Yoga of Action)",
    4: "Jnana Karma Sanyasa Yoga (The Yoga of Knowledge and Renunciation)",
    5: "Karma Sanyasa Yoga (The Yoga of Renunciation)",
    6: "Dhyana Yoga (The Yoga of Meditation)",
    7: "Jnana Vijnana Yoga (The Yoga of Knowledge and Wisdom)",
    8: "Aksara Brahma Yoga (The Yoga of the Imperishable Brahman)",
    9: "Raja Vidya Raja Guhya Yoga (The Yoga of Royal Knowledge and Secret)",
    10: "Vibhuti Yoga (The Yoga of Divine Manifestations)",
    11: "Viswarupa Darsana Yoga (The Yoga of Universal Form)",
    12: "Bhakti Yoga (The Yoga of Devotion)",
    13: "Ksetra Ksetrajna Vibhaga Yoga (The Yoga of Field and Field-Knower)",
    14: "Gunatraya Vibhaga Yoga (The Yoga of Three Gunas)",
    15: "Purushottama Yoga (The Yoga of the Supreme Person)",
    16: "Daivasura Sampad Vibhaga Yoga (The Yoga of Divine and Demoniac Natures)",
    17: "Sraddhatraya Vibhaga Yoga (The Yoga of Three Types of Faith)",
    18: "Moksha Sanyasa Yoga (The Yoga of Liberation by Renunciation)"
}

async def store_chapter_titles():
    try :
        for chapter_id , title in chapter_titles.items():
            chapter_data = {
                'chapter_id' : chapter_id,
                'title' : title,
            }

            result = chapters_collection.insert_one(chapter_data)
            print(f"Stored chapter :", result)
    
    except Exception as e:
        print(f"Error storing chapter titles: {e}")

async def main():
    try:
        # await store_chapter_titles()
        # await get_playlist_videos(API_KEY, PLAYLIST_ID)
        model = configuration_gemini()
        await generate_verse(model, 1)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())