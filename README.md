# 🥗 LastBite – AI Food Survival Tool

> **Know what you have. Waste nothing.**

LastBite is a web application that scans your fridge using AI, tracks food freshness, calculates how many days of meals you have, and suggests recipes before anything expires.

---

## Features

| Feature | Description |
|---|---|
| 📸 **AI Food Scan** | Upload a fridge photo — GPT-4o Vision detects every food item and counts real quantities |
| 🧺 **Pantry Tracker** | Tracks freshness of each item with a live colour-coded expiry countdown |
| ⏱ **Survival Runway** | Calculates how many days of meals you can make from your current stock |
| 🍳 **Recipe Suggestions** | GPT-4o suggests recipes from what you have, prioritising expiring ingredients |

---

## Technology

- **Backend:** Python, FastAPI
- **AI / Vision:** OpenAI GPT-4o Vision API
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript (no framework)

---

## How It Works

### AI Scanning (GPT-4o Vision)
A fridge photo is sent to OpenAI's GPT-4o Vision model. It looks at the actual image and identifies every food item with realistic quantities — for example "a carton of 12 eggs", "6 lemons", "2 chicken breasts". Results are returned as structured JSON.

### Freshness Tracking
Each food item has a known shelf life (e.g. chicken = 2 days, rice = 180 days). The app tracks when each item was added and counts down the days remaining. Items are colour-coded:
- 🟢 **Green** — Fresh (more than 3 days)
- 🟠 **Orange** — Expiring soon (1–3 days)
- 🔴 **Red** — Expired

### Survival Runway
Each food category contributes a different number of meals (protein = 2 meals, grain = 3 meals, vegetable = 0.75 meals, etc.). Total meals divided by 3 gives the number of survival days.

### Recipe Suggestions
GPT-4o receives your ingredient list with expiry information and generates 5 practical recipes using only what you have. Ingredients expiring soon are flagged so you cook them first.

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your API key

Create a `.env` file in the project folder:

```
OPENAI_API_KEY=your-openai-api-key-here
```

Get a free API key at **https://platform.openai.com**. Add at least $5 credit to activate.

### 3. Start the server

```bash
uvicorn main:app --port 8000
```

### 4. Open the app

Go to **http://localhost:8000** in your browser.

---

## Using the App

### Scan Tab
Upload a photo of your fridge or pantry. GPT-4o Vision analyses the image and detects all food items with quantities. Review the results, adjust if needed, and click **Add All to Pantry**.

Click **Scan Again** to clear everything and start fresh.

### Pantry Tab
All your food items with colour-coded freshness badges. Add items manually with **+ Add Item** or remove them with the × button. Click **🗑 Clear All** to empty the pantry.

### Survival Tab
Shows your survival runway — how many days of meals you can make. Critical items (expiring within 3 days) are highlighted separately with a warning.

### Recipes Tab
AI-generated recipes based exactly on what is in your pantry. Click **Refresh** to generate new suggestions. Recipes using expiring ingredients are shown with a priority warning.

---

## Project Structure

```
LastBite/
├── main.py            # FastAPI server — all API endpoints
├── ai_service.py      # GPT-4o Vision scanning + recipe generation
├── freshness.py       # Freshness rules and survival runway calculation
├── requirements.txt   # Python dependencies
├── .env.example       # API key format template (copy to .env)
├── Procfile           # Cloud deployment config (Railway / Render)
└── static/
    ├── index.html     # Single-page app — 4 tabs
    ├── style.css      # Mobile-first CSS styling
    └── app.js         # All frontend JavaScript logic
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/scan` | Scan a photo with GPT-4o Vision |
| GET | `/api/pantry` | List all pantry items |
| POST | `/api/pantry` | Add one item manually |
| POST | `/api/pantry/bulk` | Add multiple items after a scan |
| DELETE | `/api/pantry` | Clear all pantry items |
| DELETE | `/api/pantry/{id}` | Remove a single item |
| GET | `/api/runway` | Get survival runway stats |
| GET | `/api/recipes` | Get AI recipe suggestions |

---

## Security

The OpenAI API key is stored in a `.env` file which is excluded from version control via `.gitignore`. The code reads it as an environment variable:

```python
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

A `.env.example` file is included so anyone running the project knows what to create — without exposing the actual key.

---

## Notes

- Each scan costs approximately $0.01–$0.02 using GPT-4o Vision
- The database `lastbite.db` is created automatically on first run
- Do not commit `.env` or `lastbite.db` to version control
