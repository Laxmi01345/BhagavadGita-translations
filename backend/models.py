from pydantic import BaseModel
from typing import Dict,List

class Verse(BaseModel):
    verse_id : int
    sanskrit_text: list[str]
    transliteration : list[str]
    word_by_word: Dict[str,str]
    translation : str
    interpretation :  list[str]
    chapter_id:str
    timestamp: Dict[str,float]
    

class Chapters (BaseModel):
     title : str
     chapter_id : int
     video_url : str
     verses : List[Verse]



