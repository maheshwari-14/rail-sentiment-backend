from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from owlready2 import get_ontology, sync_reasoner, default_world
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import os
import traceback
import csv
from io import StringIO

# Initialize NLP Model
nltk.download('vader_lexicon', quiet=True)
sia = SentimentIntensityAnalyzer()

router = APIRouter()
ONTO_FILE = "railway-sentiment.owl"

class TweetRequest(BaseModel):
    datasetName: str
    tweets: list[str]

def get_text_score(text: str) -> int:
    score = sia.polarity_scores(text)['compound']
    if score > 0.05: return 1
    elif score < -0.05: return -1
    return 0

def categorize_tweet(text: str) -> str:
    text_lower = text.lower()
    if any(word in text_lower for word in ['clean', 'dirty', 'washroom', 'garbage']): return 'Cleanliness'
    if any(word in text_lower for word in ['staff', 'tc', 'tt', 'rude', 'polite']): return 'StaffBehaviour'
    if any(word in text_lower for word in ['late', 'delay', 'time', 'punctual']): return 'Punctuality'
    if any(word in text_lower for word in ['police', 'rpf', 'steal', 'theft', 'safe']): return 'Security'
    return 'Timeliness'

# --- CORE INFERENCE LOGIC ---
def run_protege_inference(dataset_name: str, tweets_list: list[str]):
    abs_path = os.path.abspath(ONTO_FILE)
    if not os.path.exists(ONTO_FILE):
        raise HTTPException(status_code=400, detail=f"Ontology file missing at {abs_path}.")

    results = {
        "Cleanliness": {"Positive": 0, "Neutral": 0, "Negative": 0},
        "Staff Behaviour": {"Positive": 0, "Neutral": 0, "Negative": 0},
        "Punctuality": {"Positive": 0, "Neutral": 0, "Negative": 0},
        "Security": {"Positive": 0, "Neutral": 0, "Negative": 0},
        "Timeliness": {"Positive": 0, "Neutral": 0, "Negative": 0},
    }

    try:
        onto = get_ontology(ONTO_FILE).load()

        for i, tweet in enumerate(tweets_list):
            if not tweet.strip(): continue
                
            val = get_text_score(tweet)
            cat = categorize_tweet(tweet)
            display_cat = "Staff Behaviour" if cat == "StaffBehaviour" else cat
            
            if not hasattr(onto, "Train"):
                raise AttributeError("Class 'Train' not found in ontology.")

            train_instance = onto.Train(f"Train_instance_{i}")
            prop_name = f"has{cat}"
            
            if hasattr(onto, prop_name):
                setattr(train_instance, prop_name, [val])
            else:
                raise AttributeError(f"Data property '{prop_name}' not found.")
            
            with onto:
                sync_reasoner()
            
            inferred = train_instance.hasSentiment[0] if getattr(train_instance, "hasSentiment", []) else val
            
            if inferred == 1: results[display_cat]["Positive"] += 1
            elif inferred == -1: results[display_cat]["Negative"] += 1
            else: results[display_cat]["Neutral"] += 1
                
        if hasattr(onto, 'destroy'):
            onto.destroy()
                
        return {"dataset": dataset_name, "analysis": results}
    
    except Exception as e:
        traceback.print_exc()
        if 'onto' in locals() and hasattr(onto, 'destroy'):
            onto.destroy()
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINTS ---

@router.post("/analyze")
async def process_tweets(request: TweetRequest):
    # Handles manual text pasting
    return run_protege_inference(request.datasetName, request.tweets)

@router.post("/analyze-file")
async def process_file(datasetName: str = Form(...), file: UploadFile = File(...)):
    # Handles .txt and .csv file uploads
    if not file.filename.endswith(('.txt', '.csv')):
        raise HTTPException(status_code=400, detail="Only .txt and .csv files are supported")
    
    content = await file.read()
    decoded_content = content.decode('utf-8')
    tweets_list = []

    if file.filename.endswith('.csv'):
        # Parse CSV (assuming tweets are in the first column)
        csv_reader = csv.reader(StringIO(decoded_content))
        for row in csv_reader:
            if row: tweets_list.append(row[0])
    else:
        # Parse TXT
        tweets_list = decoded_content.split('\n')

    return run_protege_inference(datasetName, tweets_list)