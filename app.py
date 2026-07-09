import os
import re
import pickle
import string
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Paths to models
MODELS_DIR = "models"
VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")
MODEL_PATH = os.path.join(MODELS_DIR, "model.pkl")

# Global variables for model and vectorizer
vectorizer = None
model = None
feature_names = None
word_weights = {}

def load_ml_model():
    global vectorizer, model, feature_names, word_weights
    if os.path.exists(VECTORIZER_PATH) and os.path.exists(MODEL_PATH):
        try:
            with open(VECTORIZER_PATH, 'rb') as f:
                vectorizer = pickle.load(f)
            with open(MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            
            # Extract weights for explainability
            feature_names = vectorizer.get_feature_names_out()
            coefficients = model.coef_[0]
            
            # Since model.classes_ is ['FAKE', 'REAL']:
            # Class 0: FAKE, Class 1: REAL
            # Positive coefficients lean towards REAL, negative lean towards FAKE.
            word_weights = {word: float(coef) for word, coef in zip(feature_names, coefficients)}
            print("Successfully loaded ML model and vectorizer.")
            return True
        except Exception as e:
            print(f"Error loading pickle files: {e}")
            return False
    else:
        print("Model files not found. Training model now...")
        try:
            from train_model import train
            train()
            return load_ml_model()
        except Exception as te:
            print(f"Failed to auto-train model: {te}")
            return False

# Initialize model
load_ml_model()

# --- NLP / Lexical Analysis Helpers ---

def get_syllables_count(word):
    """Estimate syllables in a word."""
    word = word.lower().strip(string.punctuation)
    if not word:
        return 0
    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_char_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_char_is_vowel:
            count += 1
        prev_char_is_vowel = is_vowel
    
    # Ignore silent 'e' at the end of word
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)

def calculate_readability(text):
    """Approximate Flesch Reading Ease score and grade level."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    sentence_count = max(1, len(sentences))
    
    words = text.split()
    word_count = max(1, len(words))
    
    total_syllables = sum(get_syllables_count(w) for w in words)
    
    # Flesch Reading Ease formula
    # FRE = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    fre = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (total_syllables / word_count)
    fre = max(0, min(100, fre))
    
    # Map FRE to readability grade
    if fre >= 90:
        level = "Very Easy (5th Grade)"
    elif fre >= 80:
        level = "Easy (6th Grade)"
    elif fre >= 70:
        level = "Fairly Easy (7th Grade)"
    elif fre >= 60:
        level = "Standard (8th-9th Grade)"
    elif fre >= 50:
        level = "Fairly Difficult (10th-12th Grade)"
    elif fre >= 30:
        level = "Difficult (College)"
    else:
        level = "Very Confusing (College Graduate)"
        
    return {
        "score": round(fre, 1),
        "level": level,
        "sentences": sentence_count,
        "words": word_count
    }

def calculate_sentiment(text):
    """Determine a sentiment score based on basic vocabulary checks."""
    pos_words = {"good", "great", "excellent", "happy", "positive", "success", "major", "breakthrough", 
                 "historic", "progress", "advance", "benefit", "win", "support", "development", "agreement", "achieve"}
    neg_words = {"bad", "worst", "crisis", "fail", "failure", "scandal", "corruption", "poison", "harm", 
                 "damage", "attack", "death", "kill", "disaster", "collapse", "fake", "conspiracy", "scared", "lie"}
    
    words = [w.lower().strip(string.punctuation) for w in text.split()]
    pos_count = sum(1 for w in words if w in pos_words)
    neg_count = sum(1 for w in words if w in neg_words)
    
    total = pos_count + neg_count
    if total == 0:
        score = 50.0  # Neutral
        label = "Neutral"
    else:
        # Scale score from 0 (very negative) to 100 (very positive)
        score = 50.0 + ((pos_count - neg_count) / total) * 50.0
        if score > 60:
            label = "Positive"
        elif score < 40:
            label = "Negative"
        else:
            label = "Neutral"
            
    return {
        "score": round(score, 1),
        "label": label,
        "positive_count": pos_count,
        "negative_count": neg_count
    }

def calculate_clickbait_score(title, text):
    """Assess likelihood of title or headline being clickbait."""
    score = 0
    reasons = []
    
    if not title:
        return {"score": 0, "rating": "Low", "reasons": []}
    
    # 1. Check for ALL CAPS (excluding small words)
    words = title.split()
    cap_words = [w for w in words if w.isupper() and len(w) > 1]
    if len(words) > 0 and (len(cap_words) / len(words)) > 0.4:
        score += 30
        reasons.append("High density of ALL CAPS words")
        
    # 2. Check for exclamation marks
    if "!" in title:
        score += 20
        reasons.append("Contains exclamation mark (!)")
        
    # 3. Check for question mark (often used in speculative clickbait)
    if "?" in title:
        score += 15
        reasons.append("Contains question mark (?)")
        
    # 4. Clickbait trigger phrases
    clickbait_triggers = [
        r"\byou won't believe\b", r"\bshocking\b", r"\bexposed\b", r"\bsecret\b", r"\bmagic\b", 
        r"\bmiracle\b", r"\bnever before seen\b", r"\bwhat happened next\b", r"\bwill blow your mind\b",
        r"\bthis is why\b", r"\bbreaking\b", r"\bviral\b", r"\bgone wrong\b", r"\bscientists reveal\b"
    ]
    title_lower = title.lower()
    for trigger in clickbait_triggers:
        if re.search(trigger, title_lower):
            score += 25
            reasons.append(f"Contains sensory/clickbait word: '{re.findall(trigger, title_lower)[0]}'")
            
    # 5. Starts with numbers (e.g. "15 facts about...")
    if re.match(r"^\d+", title.strip()):
        score += 15
        reasons.append("Starts with a list number")
        
    score = min(100, score)
    
    if score >= 60:
        rating = "High"
    elif score >= 30:
        rating = "Medium"
    else:
        rating = "Low"
        
    return {
        "score": score,
        "rating": rating,
        "reasons": reasons
    }

# --- Routes ---

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Scrapes news article title and text content from a given URL."""
    data = request.json or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Extract title
        title = ""
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text().strip()
        elif soup.title:
            title = soup.title.get_text().strip()
            
        # Clean soup: decompose scripting, navigation, header, footer elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            element.decompose()
            
        # Find paragraphs
        paragraphs = soup.find_all('p')
        text_content = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30])
        
        # Fallback if no clean paragraphs are found
        if not text_content:
            text_content = soup.get_text()
            # Simple cleanup of empty lines
            text_content = "\n".join([line.strip() for line in text_content.split('\n') if line.strip()])
            
        # Limit scraped text length to avoid overloading
        text_content = text_content[:15000]
        
        return jsonify({
            "title": title,
            "text": text_content
        })
    except Exception as e:
        return jsonify({"error": f"Failed to scrape URL: {str(e)}"}), 500

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyzes a news text and calculates classification metrics and highlights."""
    # Ensure model is loaded
    if model is None or vectorizer is None:
        success = load_ml_model()
        if not success:
            return jsonify({"error": "Machine learning model not loaded and training failed"}), 500
            
    data = request.json or {}
    text = data.get('text', '').strip()
    title = data.get('title', '').strip()
    
    if not text:
        return jsonify({"error": "No news text content provided"}), 400
        
    # Combine title and text for vectorizer matching the training schema
    combined_text = (title + " " + text) if title else text
    
    # 1. Model Prediction
    features_vec = vectorizer.transform([combined_text])
    prediction = model.predict(features_vec)[0]  # 'REAL' or 'FAKE'
    
    # Get probabilities
    probs = model.predict_proba(features_vec)[0]
    classes = list(model.classes_)  # ['FAKE', 'REAL']
    fake_idx = classes.index('FAKE')
    real_idx = classes.index('REAL')
    
    fake_prob = round(float(probs[fake_idx]) * 100, 1)
    real_prob = round(float(probs[real_idx]) * 100, 1)
    
    confidence = real_prob if prediction == 'REAL' else fake_prob
    
    # 2. Scored highlights (Explainable AI)
    # Split text into tokens keeping track of punctuation
    # Pattern grabs words or whitespace or punctuation
    tokens = re.findall(r"\w+|[^\w\s]|\s+", text)
    
    highlighted_tokens = []
    current_tokens_weights = []
    
    for token in tokens:
        # Check if it is a word token (not whitespace/punctuation)
        if re.match(r"^\w+$", token):
            word_lower = token.lower()
            weight = word_weights.get(word_lower, 0.0)
            
            # We ignore very tiny coefficients to focus on significant words
            if abs(weight) > 0.15:
                leaning = 'real' if weight > 0.0 else 'fake'
                highlighted_tokens.append({
                    "text": token,
                    "weight": round(weight, 3),
                    "leaning": leaning
                })
                # Save details for summary statistics
                current_tokens_weights.append((token, weight))
                continue
                
        # Fallback or punctuation / whitespace / low-weight words
        highlighted_tokens.append({
            "text": token,
            "weight": 0.0,
            "leaning": "neutral"
        })
        
    # Sort and extract top contributing words inside the current text
    # FAKE contributors (negative weights)
    fake_words_in_text = sorted([item for item in current_tokens_weights if item[1] < 0], key=lambda x: x[1])
    # REAL contributors (positive weights)
    real_words_in_text = sorted([item for item in current_tokens_weights if item[1] > 0], key=lambda x: x[1], reverse=True)
    
    # Deduplicate lists by lowercased word while preserving order
    def get_top_unique(items, limit=8):
        seen = set()
        unique = []
        for word, val in items:
            wl = word.lower()
            if wl not in seen:
                seen.add(wl)
                unique.append({"word": word, "weight": round(val, 3)})
            if len(unique) >= limit:
                break
        return unique

    top_fake_words = get_top_unique(fake_words_in_text)
    top_real_words = get_top_unique(real_words_in_text)
    
    # 3. Calculate secondary lexical features
    readability = calculate_readability(text)
    sentiment = calculate_sentiment(text)
    clickbait = calculate_clickbait_score(title, text)
    
    return jsonify({
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": {
            "FAKE": fake_prob,
            "REAL": real_prob
        },
        "highlighted_tokens": highlighted_tokens,
        "top_fake_words": top_fake_words,
        "top_real_words": top_real_words,
        "readability": readability,
        "sentiment": sentiment,
        "clickbait": clickbait
    })

if __name__ == '__main__':
    # Using port 5000 as configured
    app.run(debug=True, port=5000)
