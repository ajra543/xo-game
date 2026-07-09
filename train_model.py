import os
import pickle
import urllib.request
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Configuration
DATASET_URL = "https://raw.githubusercontent.com/lutzhamel/fake-news/master/data/fake_or_real_news.csv"
DATA_DIR = "data"
MODELS_DIR = "models"
DATA_PATH = os.path.join(DATA_DIR, "fake_or_real_news.csv")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")
MODEL_PATH = os.path.join(MODELS_DIR, "model.pkl")

# Substantial fallback synthetic dataset in case of offline/network issues
FALLBACK_DATA = [
    # Fake News
    {"title": "SHOCKING: Miracle cure for cancer discovered in common backyard weed!", "text": "You won't believe this shocking conspiracy! Big pharma is hiding the absolute truth. An inside source exposed the secret miracle cure that heals cancer in 24 hours. They don't want you to know about this amazing secret. Share before they take this video down!", "label": "FAKE"},
    {"title": "The government is secretly controlling the weather using giant lasers", "text": "Unbelievable reports expose the hidden government agenda to manipulate the climate. Insiders reveal secret lasers are creating storms. This is the truth they are desperate to hide from the public.", "label": "FAKE"},
    {"title": "BREAKING: Aliens landed in New York yesterday and officials are hiding it", "text": "A shocking leak from a top military scientist exposes that aliens have landed. The government quickly covered up the landing site. Do not believe the fake news media reports about a simple meteor shower. The truth is out there!", "label": "FAKE"},
    {"title": "Miracle weight loss pill melts fat overnight without diet or exercise", "text": "Exposed! The amazing weight loss secret doctors are hiding. This miracle pill is proven to burn fat instantly while you sleep. Inside sources say the FDA is trying to ban it to protect health corporations.", "label": "FAKE"},
    {"title": "Shocking truth revealed about the fake moon landing coordinates", "text": "A secret whistleblower has exposed that the Apollo 11 landing was staged in a Hollywood studio. Shocking new details prove the entire mission was fabricated to deceive the public.", "label": "FAKE"},
    {"title": "You won't believe what this politician did behind closed doors!", "text": "A sensational scandal has been exposed. Insider reports reveal shocking secrets about corruption and bribes. The fake news media is refusing to cover this explosive conspiracy.", "label": "FAKE"},
    {"title": "Secret formula cures aging in just three days, scientists claim", "text": "An amazing chemical breakthrough has been hidden from the public. This secret drug reverses cell aging. Big pharmaceutical giants are trying to suppress the study to keep selling their expensive products.", "label": "FAKE"},
    {"title": "BREAKING NEWS: Global economy to collapse next Tuesday, buy gold now", "text": "A top-secret warning has leaked from the world financial elite. The entire economic system will collapse in days. Experts warn you must buy gold immediately to survive the coming dark times.", "label": "FAKE"},
    {"title": "Shocking conspiracy: Water supplies are poisoned with mind-control agents", "text": "Leaked documents show a sinister plot to control public behavior. Chemicals are being added to the city water supply to make people obedient. Share this shocking truth with everyone!", "label": "FAKE"},
    {"title": "Famous actor reveals the secret society controlling Hollywood", "text": "In a shocking interview that was immediately deleted from the internet, the actor exposed details about a secret cult that controls major movies and actors. The truth is finally coming to light.", "label": "FAKE"},
    
    # Real News
    {"title": "Federal Reserve raises interest rates by a quarter point to curb inflation", "text": "The Federal Reserve announced on Wednesday that it is raising its benchmark interest rate by 0.25%. According to officials, the central bank aims to slow inflation without tipping the economy into a recession. The rate hike was widely expected by market analysts and economists.", "label": "REAL"},
    {"title": "NASA Mars Rover finds evidence of ancient liquid water in lake bed", "text": "Scientists at NASA reported that the Mars Perseverance rover has analyzed soil samples indicating that liquid water once flowed inside the Jezero Crater. The study, published in the journal Nature, suggests that the lake bed was active billions of years ago and could have hosted microbial life.", "label": "REAL"},
    {"title": "Prime Minister signs historic trade agreement with neighboring countries", "text": "During the bilateral summit on Tuesday, the Prime Minister signed a new trade deal that lowers tariffs on agricultural and electronic exports. Officials said the treaty is expected to boost GDP growth by 1.5% over the next decade and create thousands of jobs in manufacturing.", "label": "REAL"},
    {"title": "Local government announces new environmental initiative for city parks", "text": "The city council voted unanimously to allocate $5 million for expanding green spaces and planting native trees. According to the official press release, the project will begin next month and aims to reduce urban heat island effects and improve air quality in residential areas.", "label": "REAL"},
    {"title": "New clinical trial shows highly positive results for malaria vaccine", "text": "Researchers at Oxford University published a study detailing the phase three clinical trials of a new malaria vaccine. The trials, which involved over 5,000 children across East Africa, demonstrated an efficacy rate of 77%, representing a major milestone in public health.", "label": "REAL"},
    {"title": "Elections commission reports record voter turnout in midterms", "text": "According to the official report released by the State Elections Commission, over 65% of registered voters cast their ballots. Representatives from both political parties attributed the surge to increased registration efforts and interest in key congressional races.", "label": "REAL"},
    {"title": "Supreme Court rules on landmark environmental regulation case", "text": "In a 6-3 decision, the Supreme Court ruled that the EPA has the authority to regulate carbon emissions from power plants under the Clean Air Act. Justice Robert wrote the majority opinion, stating that the law clearly grants the federal agency the power to address air pollution.", "label": "REAL"},
    {"title": "Global summit on climate change begins in Geneva with pledge to cut carbon", "text": "Delegates from over 190 nations gathered in Geneva on Monday for the opening of the UN Climate Conference. In his opening address, the Secretary-General urged world leaders to commit to binding carbon reduction targets to prevent global temperatures from rising further.", "label": "REAL"},
    {"title": "Technological firm launches energy-efficient solar cells for homes", "text": "A leading renewable energy company announced a new line of residential solar panels that are 20% more efficient than standard models. According to the company's technical specifications, the panels use advanced silicon technology to generate more power in low-light conditions.", "label": "REAL"},
    {"title": "Health department issues guidelines for upcoming flu season", "text": "Public health officials held a press conference on Thursday to issue recommendations for the seasonal influenza vaccine. The department advises all citizens, particularly the elderly and immunocompromised, to receive their vaccinations before the end of October.", "label": "REAL"}
] * 5  # Duplicate data to give TF-IDF a bit more baseline rows for model fitting

def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

def download_dataset():
    if os.path.exists(DATA_PATH):
        print(f"Dataset already exists at {DATA_PATH}. Skipping download.")
        return True
    
    print(f"Downloading dataset from {DATASET_URL}...")
    try:
        # Set a user-agent to avoid HTTP 403 Forbidden errors if github requires it
        req = urllib.request.Request(
            DATASET_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(DATA_PATH, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Dataset successfully downloaded and saved to {DATA_PATH}")
        return True
    except Exception as e:
        print(f"Warning: Failed to download dataset due to error: {e}")
        print("We will fall back to training on a high-quality synthetic dataset.")
        return False

def train():
    ensure_directories()
    download_success = download_dataset()
    
    df = None
    if download_success and os.path.exists(DATA_PATH):
        try:
            print("Reading dataset...")
            # Some versions might have a header row and columns: unnamed: 0, title, text, label
            df = pd.read_csv(DATA_PATH)
            # Basic validation
            if 'text' not in df.columns or 'label' not in df.columns:
                print("CSV format not matching expected columns ('text', 'label'). Falling back to synthetic.")
                df = None
        except Exception as e:
            print(f"Error reading CSV: {e}. Falling back to synthetic.")
            df = None
            
    if df is None:
        print("Using synthetic fallback dataset for training...")
        df = pd.DataFrame(FALLBACK_DATA)
    
    # Preprocessing
    df = df.dropna(subset=['text', 'label'])
    # Make sure labels are standardized to 'REAL' and 'FAKE'
    df['label'] = df['label'].str.upper().str.strip()
    df = df[df['label'].isin(['REAL', 'FAKE'])]
    
    # Merge title and text if title exists
    if 'title' in df.columns:
        df['title'] = df['title'].fillna('')
        X = df['title'] + " " + df['text']
    else:
        X = df['text']
        
    y = df['label']
    
    print(f"Dataset size: {len(X)} records.")
    print("Splitting into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Vectorizing text using TF-IDF...")
    # max_features=5000 limits the size of the vocabulary, making serialization lightweight and fast.
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.7, max_features=5000)
    X_train_vectorized = vectorizer.fit_transform(X_train)
    X_test_vectorized = vectorizer.transform(X_test)
    
    print("Training Logistic Regression classifier...")
    # Logistic Regression gives us clean probability values (predict_proba) for confidence metrics
    model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    model.fit(X_train_vectorized, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_vectorized)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model validation accuracy: {accuracy * 100:.2f}%")
    
    # Save objects
    print(f"Saving vectorizer to {VECTORIZER_PATH}...")
    with open(VECTORIZER_PATH, 'wb') as f:
        pickle.dump(vectorizer, f)
        
    print(f"Saving model to {MODEL_PATH}...")
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
        
    print("Model training pipeline complete!")

if __name__ == "__main__":
    train()
