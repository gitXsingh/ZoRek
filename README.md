# ZoRek – Entertainment Bot 🎬🎵🍕

ZoRek is an entertainment chatbot built for **Zoho SalesIQ platform** that provides personalized recommendations for movies, books, games, food, and music, along with event booking capabilities. The bot consists of four Deluge handler scripts that work together to create a seamless conversational experience.

**Live Demo**: https://zorek.onrender.com
<img width="1919" height="964" alt="image" src="https://github.com/user-attachments/assets/6ef96608-d5d9-420b-94f2-9aa1203738d7" />


## 🎯 Features

- **Suggest Something**: Get recommendations for Movies, Books, Games, Food, and Music with preference collection
- **Book an Event**: Find concerts, talkshows, theater events, and movies near you (200+ Indian cities)
- **My Pick Combo**: Get a creative combination of Movie + Song + Food based on your mood
- **OAuth 2.0 Integration**: Spotify authentication for personalized music recommendations
- **AI Commentary**: Optional AI-powered fun blurbs (requires OpenAI API key)
- **Google Sheets Logging**: All interactions are logged for analytics

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 18+ and npm (optional, for React frontend)
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

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
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

4. **Run the application**
   ```bash
   python app.py
   # or with gunicorn:
   gunicorn app:app
   ```

5. **Access the application**
   - Local: http://localhost:5000
   - Live: https://zorek.onrender.com

## 📋 Zoho SalesIQ Bot Setup

### Handler Scripts

The bot consists of four Deluge handler scripts located in `zohoscripts/`:

1. **TriggerHandler.deluge** - Initial greeting when chat starts
2. **MessageHandler.deluge** - Routes user messages and handles card selections
3. **ContextHandler.deluge** - Core logic for all bot contexts (suggest, events, combo)
4. **FailureHandler.deluge** - Error handling and fallback messages

### Installation Steps

1. **Extract ZoRek_bot.zip** (contains all handler scripts)
2. **Access Zoho SalesIQ Bot Builder**
3. **Upload each handler script:**
   - TriggerHandler.deluge → Trigger Handler section
   - MessageHandler.deluge → Message Handler section
   - ContextHandler.deluge → Context Handler section
   - FailureHandler.deluge → Failure Handler section
4. **Configure Backend URL:** Ensure `https://zorek.onrender.com` is accessible
5. **Test Each Feature:**
   - Suggest Something (all categories)
   - Book an Event (various cities)
   - My Pick Combo
   - Connect to Spotify
6. **Verify Session Storage:** Test card selection by number (1-10)

For detailed documentation, see [ZoRek_Bot_Documentation.md](./ZoRek_Bot_Documentation.md)

## 🔌 API Endpoints

### Bot Endpoints (For Zoho SalesIQ)

#### `POST /suggest_cards`
Get suggestions in SalesIQ card format.

**Request:**
```json
{
  "category": "movies",
  "prefs": {
    "genre": "Action",
    "minImdb": "7.0",
    "year": "2015"
  }
}
```

**Response:**
```json
{
  "type": "multiple-product",
  "elements": [
    {
      "id": "card_1",
      "title": "Inception (2010)",
      "subtitle": "Sci-Fi · IMDb 8.8",
      "image": "https://...",
      "actions": [
        {
          "label": "View",
          "type": "url",
          "link": "https://www.imdb.com/title/tt1375666/"
        }
      ]
    }
  ]
}
```

#### `POST /events_cards`
Get events in SalesIQ card format.

**Request:**
```json
{
  "category": "concerts",
  "city": "Mumbai"
}
```

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

### OAuth Endpoints

#### `GET /oauth/spotify/start`
Redirect to Spotify authorization page.

#### `GET /oauth/spotify/callback`
Handle Spotify OAuth callback.

#### `GET /oauth/spotify/status`
Check Spotify connection status.

**Response:**
```json
{
  "connected": true,
  "mode": "user"
}
```

### Utility Endpoints

#### `GET /health_check`
Check health status of all APIs.

#### `POST /ai_commentary`
Get AI-generated commentary (requires OpenAI API key).

## 🔧 Third-Party Integrations

- **Movies**: OMDb API, TMDB API
- **Books**: Google Books API
- **Games**: CheapShark API
- **Food**: Spoonacular API
- **Music**: Spotify API (OAuth 2.0), iTunes API (fallback)
- **Events**: SeatGeek API, BookMyShow links, Google Search
- **Analytics**: Sheet.best (Google Sheets logging)
- **AI**: OpenAI API (optional commentary)

## 📊 Key Features Coverage

### Core Requirements ✅

1. **Suggest Something**
   - ✅ Multiple categories (Movies, Books, Games, Food, Music)
   - ✅ Preference collection before suggestions
   - ✅ Third-party API integration
   - ✅ Card-based display format

2. **Book an Event**
   - ✅ Multiple event types (Movies, Concerts, Talkshow, Theater, Sports)
   - ✅ Location-based search (200+ Indian cities)
   - ✅ Action items (booking links)
   - ✅ Third-party integration (BookMyShow, SeatGeek)

3. **Custom Feature (My Pick Combo)**
   - ✅ Creative multi-modal recommendations
   - ✅ Mood-based personalization
   - ✅ Combines multiple entertainment types

### Brownie Points ✅

1. **OAuth 2.0 Authentication**
   - ✅ Spotify OAuth integration
   - ✅ Secure authentication flow
   - ✅ Direct track links after connection

2. **AI Functionalities**
   - ✅ Backend supports OpenAI integration
   - ✅ Optional AI commentary on recommendations

3. **Data Collection**
   - ✅ Google Sheets logging
   - ✅ Comprehensive interaction tracking
   - ✅ Analytics-ready data structure

## 🏗️ Integration Architecture

The bot uses a **minimal integration pattern** that separates concerns:

```
User → Zoho SalesIQ → Deluge Handlers → Backend API → Third-Party APIs
                ↓
         Session Storage
                ↓
         Card URL Retrieval
```

### Minimal Integration Approach

1. **Deluge Scripts (Frontend Logic):**
   - Handle conversation flow
   - Collect user preferences
   - Format responses
   - Manage session storage

2. **Backend API (Business Logic):**
   - Fetches data from third-party APIs
   - Processes and filters results
   - Formats card data
   - Handles logging

3. **Zoho SalesIQ (Platform):**
   - Provides chat interface
   - Manages visitor sessions
   - Handles message routing
   - Stores session data

## 🚢 Deployment

### Deploy to Render

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository**
3. **Set environment variables** in Render dashboard
4. **Set build command**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set start command**:
   ```bash
   gunicorn app:app
   ```

## 📄 Project Structure

```
ZoRek/
├── app.py                        # Flask backend
├── bot/
│   ├── routes.py                # Bot API endpoints
│   └── __init__.py
├── zohoscripts/
│   ├── TriggerHandler.deluge    # Initial greeting
│   ├── MessageHandler.deluge    # Message routing
│   ├── ContextHandler.deluge    # Core logic
│   └── FailureHandler.deluge    # Error handling
├── ZoRek_bot.zip                # Ready-to-use bot scripts
├── ZoRek_Bot_Documentation.md   # Detailed documentation
├── requirements.txt              # Python dependencies
└── README.md
```

## 📝 Logging

All user interactions are automatically logged to Google Sheets via Sheet.best. The log includes:
- Category, Preferences, City
- Results Count, Suggestions
- Timestamp, Endpoint

## 🔒 Security

- All API keys stored in environment variables
- CORS configured for Zoho SalesIQ domains
- OAuth 2.0 for Spotify authentication
- Proper error handling and responses

## 📚 Documentation

- **[ZoRek_Bot_Documentation.md](./ZoRek_Bot_Documentation.md)** - Complete handler scripts documentation
- Handler scripts are in `zohoscripts/` folder
- Ready-to-use zip: `ZoRek_bot.zip`

## 🐛 Troubleshooting

### API Keys Not Working
- Ensure all environment variables are set correctly
- Check that API keys are valid and have proper permissions

### Spotify OAuth Not Working
- Verify `SPOTIFY_REDIRECT_URI` matches your Spotify app settings
- Check redirect URI is added in Spotify Developer Dashboard
- Ensure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are correct

### Handler Scripts Errors
- Verify backend URL is accessible: `https://zorek.onrender.com`
- Check portal name is correctly extracted in handlers
- Ensure session storage is working properly

## 📄 License

This project is non-commercial and built for educational purposes.

## 🔗 Links

- **Live App**: https://zorek.onrender.com
- **GitHub**: https://github.com/gitXsingh/ZoRek
- **Zoho SalesIQ**: https://www.zoho.com/salesiq/

## 👥 Contributors

Built for Zoho SalesIQ Entertainment Track
