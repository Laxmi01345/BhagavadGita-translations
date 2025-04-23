
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://laxmiray013:eqUS0erE05UL41xH@cluster0.yrgzhpu.mongodb.net/"
client = MongoClient(uri, server_api=ServerApi('1'))

db = client.BhagavadGita_playlist
chapters_collection = db["Chapters"]
verses_collection = db["Verses"]

def test_connection():
    try:
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return False