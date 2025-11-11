# ZoRek - Smart Entertainment Bot

ZoRek is an AI-powered entertainment chatbot built for the **Zoho SalesIQ platform**. It provides personalized movie, book, game, food, and music recommendations to users through an interactive web chat interface.

## 🎯 Features

- **Suggest Something**: Get recommendations for Movies, Books, Games, Food, and Music
- **Book an Event**: Find concerts, talkshows, theater events, and movies near you
- **My Pick**: Get a creative combination of Movie + Song + Food based on your mood
- **OAuth 2.0 Integration**: Spotify authentication for personalized music recommendations
- **AI Commentary**: Optional AI-powered fun blurbs (requires OpenAI API key)
- **Google Sheets Logging**: All interactions are logged for analytics

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- API keys for:
  - OMDb (required)
  - TMDB (required)
  - Spoonacular (required)
  - Sheet.best (required)
  - Spotify (optional but recommended)
  - SeatGeek (optional)
  - OpenAI (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/gitXsingh/ZoRek.git
   cd ZoRek
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env and add your API keys
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Local: http://localhost:5000
   - Live: https://zorek.onrender.com

## 📋 Environment Variables

Copy `env.example` to `.env` and fill in your API keys:

```bash
OMDB_KEY=your_omdb_key_here
TMDB_KEY=your_tmdb_key_here
SPOONACULAR_KEY=your_spoonacular_key_here
SHEET_BEST_URL=https://api.sheetbest.com/sheets/your_sheet_id_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=https://zorek.onrender.com/oauth/spotify/callback
SEATGEEK_CLIENT_ID=your_seatgeek_client_id_here
OPENAI_API_KEY=your_openai_api_key_here
```

## 🔌 API Endpoints

### Main Endpoints

#### `GET /`
Renders the main chat interface.

#### `POST /recommendations`
Get combined recommendations (Movie + Song + Food).

**Request:**
```json
{
  "mood": "Happy",
  "movieGenre": "Action",
  "songType": "Pop",
  "diet": "Veg"
}
```

**Response:**
```json
{
  "movie": {
    "text": "🎬 Inception (2010)",
    "url": "https://www.imdb.com/title/tt1375666/",
    "image": "https://..."
  },
  "song": {
    "text": "🎵 Bad Guy — Billie Eilish",
    "url": "https://open.spotify.com/track/...",
    "image": "https://..."
  },
  "food": {
    "text": "🍕 Caprese Salad",
    "url": "https://...",
    "image": "https://..."
  }
}
```

#### `POST /suggest`
Get suggestions for a specific category.

**Request:**
```json
{
  "category": "Movies",
  "prefs": {
    "genre": "Drama",
    "minImdb": 7.0,
    "year": "2019"
  }
}
```

**Response:**
```json
{
  "items": [
    {
      "text": "🎬 The Shawshank Redemption (1994) — ⭐ 9.3",
      "url": "https://www.imdb.com/title/tt0111161/",
      "poster": "https://...",
      "imdbRating": "9.3",
      "year": "1994"
    }
  ]
}
```

#### `POST /events`
Get events near a city.

**Request:**
```json
{
  "category": "Concerts",
  "city": "Mumbai"
}
```

**Response:**
```json
{
  "items": [
    {
      "text": "📅 Arijit Singh Live — 2025-12-02 19:00 @ Wankhede Stadium",
      "url": "https://seatgeek.com/..."
    }
  ]
}
```

### SalesIQ Card Endpoints

#### `POST /suggest_cards`
Returns suggestions in SalesIQ card format.

**Request:**
```json
{
  "category": "Movies",
  "prefs": {
    "genre": "Action",
    "minImdb": 7.0
  }
}
```

**Response:**
```json
{
  "cards": [
    {
      "title": "Inception (2010)",
      "imageUrl": "https://...",
      "description": "⭐ 8.8",
      "action": {
        "label": "View",
        "url": "https://www.imdb.com/title/tt1375666/"
      }
    }
  ]
}
```

#### `POST /events_cards`
Returns events in SalesIQ card format.

**Request:**
```json
{
  "category": "Concerts",
  "city": "Mumbai"
}
```

**Response:**
```json
{
  "cards": [
    {
      "title": "Arijit Singh Live",
      "imageUrl": null,
      "description": "2025-12-02 19:00 @ Wankhede Stadium",
      "action": {
        "label": "Tickets",
        "url": "https://seatgeek.com/..."
      }
    }
  ]
}
```

### OAuth Endpoints

#### `GET /oauth/spotify/start`
Get Spotify authorization URL.

**Response:**
```json
{
  "auth_url": "https://accounts.spotify.com/authorize?..."
}
```

#### `GET /oauth/spotify/callback`
Handle Spotify OAuth callback.

#### `GET /oauth/spotify/status`
Check Spotify connection status.

**Response:**
```json
{
  "connected": true,
  "mode": "app"
}
```

### Utility Endpoints

#### `GET /widget_detail?email=user@example.com`
Get visitor data for SalesIQ operator widget.

**Response:**
```json
{
  "email": "user@example.com",
  "lastChoice": "Movies",
  "lastGenre": "Action",
  "lastSuggestion": "Inception (2010)",
  "timestamp": "2025-01-15T10:30:00",
  "interactionCount": 1
}
```

#### `GET /health_check`
Check health status of all APIs.

**Response:**
```json
{
  "status": "ok",
  "checks": {
    "OMDb": "PASS",
    "Books": "PASS",
    "Spoonacular": "PASS",
    "SheetBest": "PASS",
    "Local": "PASS",
    "TMDB": "PASS",
    "Spotify": "PASS"
  },
  "timestamp": "2025-01-15T10:30:00"
}
```

#### `POST /ai_commentary`
Get AI-generated commentary (requires OpenAI API key).

**Request:**
```json
{
  "movie": {"text": "Inception (2010)"},
  "song": {"text": "Bad Guy — Billie Eilish"},
  "food": {"text": "Caprese Salad"},
  "mood": "Happy"
}
```

**Response:**
```json
{
  "commentary": "For a happy mood, pair the mind-bending Inception with Billie Eilish's Bad Guy for an edgy vibe, and enjoy a fresh Caprese Salad to complete your entertainment feast!"
}
```

## 🔧 Third-Party Integrations

### Movies
- **OMDb API**: Movie search and details
- **TMDB API**: Genre-based discovery and now-playing movies

### Books
- **Google Books API**: Book recommendations by subject

### Games
- **CheapShark API**: Game search and pricing

### Food
- **Spoonacular API**: Recipe recommendations (supports vegetarian filter)

### Music
- **Spotify API**: Music recommendations (OAuth 2.0)
- **iTunes API**: Fallback music search

### Events
- **SeatGeek API**: Event listings (optional)
- **Nominatim (OpenStreetMap)**: City geocoding
- **TMDB API**: Now-playing movies

### Analytics
- **Sheet.best**: Google Sheets logging

### AI
- **OpenAI API**: AI commentary (optional)

## 🚢 Deployment

### Deploy to Render

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository**
3. **Set environment variables** in Render dashboard
4. **Set build command**: `pip install -r requirements.txt`
5. **Set start command**: `python app.py`
6. **Deploy**

### Environment Variables on Render

Add all environment variables from `.env` in the Render dashboard under "Environment".

## 📊 Testing

### Health Check
```bash
curl http://localhost:5000/health_check
```

### Test Recommendations
```bash
curl -X POST http://localhost:5000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"mood":"Happy","movieGenre":"Action","songType":"Pop","diet":"Veg"}'
```

### Test Suggest
```bash
curl -X POST http://localhost:5000/suggest \
  -H "Content-Type: application/json" \
  -d '{"category":"Movies","prefs":{"genre":"Drama","minImdb":7.0}}'
```

### Test Events
```bash
curl -X POST http://localhost:5000/events \
  -H "Content-Type: application/json" \
  -d '{"category":"Concerts","city":"Mumbai"}'
```

## 📝 Logging

All user interactions are automatically logged to Google Sheets via Sheet.best. The log includes:
- Name
- Email
- Choice (Movies/Books/Games/Food/Music)
- Genre
- Mood
- Suggestion
- Timestamp

## 🔒 Security

- All API keys are stored in environment variables
- CORS is configured for Zoho SalesIQ domains
- OAuth 2.0 is used for Spotify authentication
- All endpoints return proper error responses

## 📚 Documentation

For detailed Zoho SalesIQ integration guide, see [ZoRek_SalesIQ_Integration_Guide.md](./ZoRek_SalesIQ_Integration_Guide.md).

## 🐛 Troubleshooting

### API Keys Not Working
- Ensure all environment variables are set correctly
- Check that API keys are valid and have proper permissions
- Verify `.env` file is in the project root

### CORS Errors
- Ensure CORS is configured correctly in `app.py`
- Check that your domain is allowed in CORS settings

### Spotify OAuth Not Working
- Verify `SPOTIFY_REDIRECT_URI` matches your Spotify app settings
- Check that redirect URI is added in Spotify Developer Dashboard
- Ensure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are correct

## 📄 License

This project is non-commercial and built for educational purposes.

## 👥 Contributors

- Built for Zoho SalesIQ Entertainment Track

## 🔗 Links

- **Live App**: https://zorek.onrender.com
- **GitHub**: https://github.com/gitXsingh/ZoRek
- **Zoho SalesIQ**: https://www.zoho.com/salesiq/

## 📞 Support

For issues and questions, please open an issue on GitHub.

