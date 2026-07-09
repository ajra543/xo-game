// Global state
let activeMode = 'text'; // 'text' or 'url'
let history = [];

// Initialize Page
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    // Initialize radial circle
    setRadialConfidence(0, 'REAL');
});

// Tab Navigation
function switchTab(mode) {
    if (mode === activeMode) return;
    
    activeMode = mode;
    
    // Toggle active classes on tab buttons
    document.getElementById('tab-text').classList.toggle('active', mode === 'text');
    document.getElementById('tab-url').classList.toggle('active', mode === 'url');
    
    // Toggle active classes on input card groups
    document.getElementById('text-input-group').classList.toggle('active', mode === 'text');
    document.getElementById('url-input-group').classList.toggle('active', mode === 'url');
}

// Clear input values
function clearInputs() {
    if (activeMode === 'text') {
        document.getElementById('article-title').value = '';
        document.getElementById('article-text').value = '';
    } else {
        document.getElementById('article-url').value = '';
        document.getElementById('scraped-title').value = '';
        document.getElementById('scraped-text').value = '';
    }
}

// Scrape article from URL
async function fetchArticle() {
    const urlInput = document.getElementById('article-url');
    const url = urlInput.value.trim();
    
    if (!url) {
        alert('Please enter a valid article URL first.');
        return;
    }
    
    // UI Loading State
    const btn = document.getElementById('btn-fetch');
    const loader = document.getElementById('fetch-loader');
    const btnText = document.getElementById('fetch-btn-text');
    
    btn.disabled = true;
    loader.classList.remove('hidden');
    btnText.textContent = 'Fetching...';
    
    try {
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch article contents.');
        }
        
        // Populate inputs
        document.getElementById('scraped-title').value = data.title || '';
        document.getElementById('scraped-text').value = data.text || '';
        
    } catch (error) {
        console.error(error);
        alert(`Scraper Error: ${error.message}`);
    } finally {
        btn.disabled = false;
        loader.classList.add('hidden');
        btnText.textContent = 'Extract';
    }
}

// Run Machine Learning & Lexical Analysis
async function runAnalysis() {
    let title = '';
    let text = '';
    
    if (activeMode === 'text') {
        title = document.getElementById('article-title').value.trim();
        text = document.getElementById('article-text').value.trim();
    } else {
        title = document.getElementById('scraped-title').value.trim();
        text = document.getElementById('scraped-text').value.trim();
    }
    
    if (text.length < 30) {
        alert('Please enter or extract at least 30 characters of article body text to ensure an accurate classification.');
        return;
    }
    
    // UI Loading State
    const btn = document.getElementById('btn-analyze');
    const loader = document.getElementById('analyze-loader');
    const btnText = document.getElementById('analyze-text');
    
    btn.disabled = true;
    loader.classList.remove('hidden');
    btnText.textContent = 'Analyzing...';
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, text: text })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Analysis failed.');
        }
        
        // Render Dashboard Results
        renderResults(data, title, text);
        
        // Add to history
        addToHistory({
            title: title || 'Untitled Article Text',
            text: text,
            prediction: data.prediction,
            confidence: data.confidence,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + new Date().toLocaleDateString()
        });
        
    } catch (error) {
        console.error(error);
        alert(`Analysis Error: ${error.message}`);
    } finally {
        btn.disabled = false;
        loader.classList.add('hidden');
        btnText.textContent = 'Analyze Article';
    }
}

// Update Results View
function renderResults(data, title, text) {
    // 1. Show results container
    document.getElementById('welcome-placeholder').classList.add('hidden');
    const resultsPanel = document.getElementById('results-panel');
    resultsPanel.classList.remove('hidden');
    
    // Scroll results panel into view on mobile
    if (window.innerWidth <= 900) {
        resultsPanel.scrollIntoView({ behavior: 'smooth' });
    }
    
    // 2. Verdict Styling
    const verdictCard = document.getElementById('verdict-status-card');
    const verdictLabel = document.getElementById('verdict-label');
    const verdictSummary = document.getElementById('verdict-summary');
    
    verdictCard.classList.remove('verdict-real', 'verdict-fake');
    
    if (data.prediction === 'REAL') {
        verdictCard.classList.add('verdict-real');
        verdictLabel.textContent = 'REAL NEWS';
        verdictSummary.textContent = `The article contains vocabulary, phrasing, and source patterns highly consistent with objective reporting (Confidence: ${data.confidence}%).`;
    } else {
        verdictCard.classList.add('verdict-fake');
        verdictLabel.textContent = 'FAKE NEWS';
        verdictSummary.textContent = `The text demonstrates heavy use of clickbait headlines, emotional bias, or speculative phrases typical of fabricated stories (Confidence: ${data.confidence}%).`;
    }
    
    // 3. Radial gauge confidence circle
    setRadialConfidence(data.confidence, data.prediction);
    
    // 4. Highlighted tokens (Explainable AI)
    renderHighlights(data.highlighted_tokens);
    
    // 5. Keyword Contribution charts
    renderCharts(data.top_real_words, data.top_fake_words);
    
    // 6. Metrics Grid: Clickbait
    renderClickbait(data.clickbait);
    
    // 7. Metrics Grid: Readability
    document.getElementById('readability-level').textContent = data.readability.level.split('(')[0].trim();
    document.getElementById('readability-score').textContent = data.readability.score;
    document.getElementById('readability-progress').style.width = `${data.readability.score}%`;
    
    // 8. Metrics Grid: Sentiment
    const sentLabel = document.getElementById('sentiment-label');
    sentLabel.textContent = data.sentiment.label;
    sentLabel.classList.remove('bg-green', 'bg-blue', 'bg-red');
    if (data.sentiment.label === 'Positive') {
        sentLabel.classList.add('bg-green');
    } else if (data.sentiment.label === 'Negative') {
        sentLabel.classList.add('bg-red');
    } else {
        sentLabel.classList.add('bg-blue');
    }
    document.getElementById('sentiment-score').textContent = `${data.sentiment.score}%`;
    document.getElementById('sentiment-progress').style.width = `${data.sentiment.score}%`;
}

// Control the SVG Confidence Ring animation
function setRadialConfidence(percent, prediction) {
    const circle = document.getElementById('confidence-ring');
    const displayVal = document.getElementById('confidence-percentage');
    
    displayVal.textContent = `${percent}%`;
    
    // radius=50 -> circumference = 314.159
    const radius = 50;
    const circumference = radius * 2 * Math.PI;
    
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    
    // If percent is 0 (initial), offset = circumference
    const offset = circumference - (percent / 100) * circumference;
    circle.style.strokeDashoffset = offset;
    
    // Set circle stroke color depending on prediction
    if (prediction === 'REAL') {
        circle.style.stroke = '#10b981'; // green
    } else {
        circle.style.stroke = '#ef4444'; // red
    }
}

// Construct the Explainable AI highlight view paragraph
function renderHighlights(tokens) {
    const container = document.getElementById('highlight-viewer');
    container.innerHTML = '';
    
    tokens.forEach(token => {
        if (token.leaning === 'real') {
            const span = document.createElement('span');
            span.className = 'word-hl real-hl';
            span.title = `Real-leaning weight: +${token.weight}`;
            span.textContent = token.text;
            container.appendChild(span);
        } else if (token.leaning === 'fake') {
            const span = document.createElement('span');
            span.className = 'word-hl fake-hl';
            span.title = `Fake-leaning weight: ${token.weight}`;
            span.textContent = token.text;
            container.appendChild(span);
        } else {
            // Neutral word/punctuation/whitespace
            // Using createTextNode maintains original formatting and spaces exactly
            container.appendChild(document.createTextNode(token.text));
        }
    });
}

// Draw Keyword Bar Chart Columns
function renderCharts(realWords, fakeWords) {
    const realContainer = document.getElementById('real-words-chart');
    const fakeContainer = document.getElementById('fake-words-chart');
    
    realContainer.innerHTML = '';
    fakeContainer.innerHTML = '';
    
    // Find absolute maximum weight to scale bars relatively
    const allWeights = [...realWords.map(w => Math.abs(w.weight)), ...fakeWords.map(w => Math.abs(w.weight))];
    const maxWeight = allWeights.length > 0 ? Math.max(...allWeights) : 1.0;
    
    // Render REAL Indicators
    if (realWords.length === 0) {
        realContainer.innerHTML = '<p class="no-features-text">No significant indicators found.</p>';
    } else {
        realWords.forEach(item => {
            const widthPct = Math.max(5, (Math.abs(item.weight) / maxWeight) * 100);
            
            const row = document.createElement('div');
            row.className = 'bar-row';
            row.innerHTML = `
                <span class="bar-label" title="${item.word}">${item.word}</span>
                <div class="bar-wrapper">
                    <div class="bar-fill real-fill" style="width: ${widthPct}%"></div>
                </div>
                <span class="bar-value">+${item.weight.toFixed(2)}</span>
            `;
            realContainer.appendChild(row);
        });
    }
    
    // Render FAKE Indicators
    if (fakeWords.length === 0) {
        fakeContainer.innerHTML = '<p class="no-features-text">No significant indicators found.</p>';
    } else {
        fakeWords.forEach(item => {
            const widthPct = Math.max(5, (Math.abs(item.weight) / maxWeight) * 100);
            
            const row = document.createElement('div');
            row.className = 'bar-row';
            row.innerHTML = `
                <span class="bar-label" title="${item.word}">${item.word}</span>
                <div class="bar-wrapper">
                    <div class="bar-fill fake-fill" style="width: ${widthPct}%"></div>
                </div>
                <span class="bar-value">${item.weight.toFixed(2)}</span>
            `;
            fakeContainer.appendChild(row);
        });
    }
}

// Display Clickbait Rating & Details
function renderClickbait(clickbait) {
    const scoreText = document.getElementById('clickbait-score');
    const ratingBadge = document.getElementById('clickbait-rating');
    const progressBar = document.getElementById('clickbait-progress');
    const reasonsList = document.getElementById('clickbait-reasons');
    
    scoreText.textContent = `${clickbait.score}%`;
    ratingBadge.textContent = clickbait.rating;
    
    // Color rating badge
    ratingBadge.classList.remove('bg-green', 'bg-yellow', 'bg-red');
    if (clickbait.rating === 'Low') {
        ratingBadge.classList.add('bg-green');
    } else if (clickbait.rating === 'Medium') {
        ratingBadge.classList.add('bg-yellow');
    } else {
        ratingBadge.classList.add('bg-red');
    }
    
    progressBar.style.width = `${clickbait.score}%`;
    
    // Set progress bar color
    progressBar.classList.remove('bg-blue');
    if (clickbait.score < 30) {
        progressBar.style.backgroundColor = '#10b981'; // Green
    } else if (clickbait.score < 60) {
        progressBar.style.backgroundColor = '#eab308'; // Yellow
    } else {
        progressBar.style.backgroundColor = '#ef4444'; // Red
    }
    
    // Render reasons list
    reasonsList.innerHTML = '';
    if (clickbait.reasons.length === 0) {
        reasonsList.innerHTML = '<li>Headline metrics normal</li>';
    } else {
        clickbait.reasons.forEach(reason => {
            const li = document.createElement('li');
            li.textContent = reason;
            reasonsList.appendChild(li);
        });
    }
}

// --- History Storage Helpers ---

function loadHistory() {
    const stored = localStorage.getItem('veritruth_history');
    if (stored) {
        try {
            history = JSON.parse(stored);
        } catch (e) {
            history = [];
        }
    }
    renderHistoryList();
}

function addToHistory(item) {
    // Avoid exact duplicate headlines back-to-back
    if (history.length > 0 && history[0].title === item.title && history[0].text === item.text) {
        return;
    }
    
    history.unshift(item);
    // Keep max 8 elements
    if (history.length > 8) {
        history.pop();
    }
    
    localStorage.setItem('veritruth_history', JSON.stringify(history));
    renderHistoryList();
}

function clearHistory() {
    history = [];
    localStorage.removeItem('veritruth_history');
    renderHistoryList();
}

function renderHistoryList() {
    const list = document.getElementById('history-items');
    list.innerHTML = '';
    
    if (history.length === 0) {
        list.innerHTML = '<p class="no-history-text">No articles checked recently. Run an analysis to start building history.</p>';
        return;
    }
    
    history.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.onclick = () => loadHistoryItem(index);
        
        const verdictClass = item.prediction === 'REAL' ? 'history-real' : 'history-fake';
        
        card.innerHTML = `
            <div class="history-info">
                <span class="history-title" title="${item.title}">${item.title}</span>
                <div class="history-meta">
                    <span>Confidence: ${item.confidence}%</span>
                    <span>•</span>
                    <span>${item.timestamp}</span>
                </div>
            </div>
            <span class="history-verdict ${verdictClass}">${item.prediction}</span>
        `;
        list.appendChild(card);
    });
}

// Load a clicked history item back into inputs and re-run
function loadHistoryItem(index) {
    const item = history[index];
    if (!item) return;
    
    // Switch to text mode to show the values
    switchTab('text');
    
    document.getElementById('article-title').value = item.title;
    document.getElementById('article-text').value = item.text;
    
    // Scroll up to inputs
    document.querySelector('.app-header').scrollIntoView({ behavior: 'smooth' });
    
    // Automatically re-analyze
    runAnalysis();
}
