# 🔑 API Keys Status & Configuration

## ✅ All API Keys Are Correctly Configured

All API keys are loaded from **environment variables** - no hardcoded keys in the code.

---

## 📋 Required Environment Variables

### 1. **OMDB_KEY** (OMDb API)
- **Status**: ✅ Loaded from `os.environ.get("OMDB_KEY", "")`
- **Used in**: Movie search, movie details
- **Usage locations**:
  - `search_movies_with_filters()` - line 571, 581
  - `get_movie_recommendation_with_url()` - line 381, 386
  - `discover_movies_via_tmdb()` - line 205
- **Fallback**: Returns empty list if key missing

### 2. **TMDB_KEY** (The Movie Database API)
- **Status**: ✅ Loaded from `os.environ.get("TMDB_KEY", "")`
- **Used in**: Movie discovery by genre, trending movies, now-playing movies
- **Usage locations**:
  - `discover_movies_via_tmdb()` - line 180, 199
  - `fetch_trending_movies()` - line 535
  - `events_cards()` endpoint - line 558
- **Fallback**: Falls back to OMDb if key missing

### 3. **SPOONACULAR_KEY** (Spoonacular Food API)
- **Status**: ✅ Loaded from `os.environ.get("SPOONACULAR_KEY", "")`
- **Used in**: Food/recipe recommendations
- **Usage locations**:
  - `get_food_recommendation_with_url()` - line 513
- **Fallback**: Returns error message if key missing

### 4. **SPOTIFY_CLIENT_ID** & **SPOTIFY_CLIENT_SECRET**
- **Status**: ✅ Loaded from environment variables
- **Used in**: Spotify OAuth, music recommendations
- **Usage locations**:
  - `ensure_spotify_token()` - line 57, 58
  - `spotify_start()` - line 736, 749
  - `spotify_callback()` - line 781, 782
  - Music search functions (lines 410, 460)
- **Fallback**: Falls back to iTunes API if Spotify not configured

### 5. **SEATGEEK_CLIENT_ID** (SeatGeek Events API)
- **Status**: ✅ Loaded from `os.environ.get("SEATGEEK_CLIENT_ID", "")`
- **Used in**: Event search by location
- **Usage locations**:
  - `events_from_seatgeek()` - line 246
  - `events_cards()` endpoint - line 540
- **Fallback**: Uses fallback event links if key missing

### 6. **OPENAI_API_KEY** (OpenAI GPT API)
- **Status**: ✅ Loaded from `os.environ.get("OPENAI_API_KEY", "")`
- **Used in**: AI commentary generation
- **Usage locations**:
  - `ai_commentary()` endpoint - line 812, 826
- **Fallback**: Returns error 400 if key missing

### 7. **SHEET_BEST_URL** (Google Sheets Logging)
- **Status**: ✅ Loaded from `os.environ.get("SHEET_BEST_URL", "")`
- **Used in**: Logging user interactions to Google Sheets
- **Usage locations**:
  - All three bot endpoints: `/suggest_cards`, `/events_cards`, `/recommendations`
- **Fallback**: Logging skipped silently if URL missing (non-blocking)

---

## 🔍 Security Check

✅ **No hardcoded API keys found**  
✅ **All keys loaded from environment variables**  
✅ **`.env` file should not be committed to git**  
✅ **`load_dotenv()` called at the top of `app.py`**

---

## 📝 Environment Variables List

Add these to your `.env` file (or Render environment variables):

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

---

## ⚠️ Notes

1. **Google Books API**: No key required (free API)
2. **CheapShark API**: No key required (free API)
3. **iTunes Search API**: No key required (free API)
4. **OpenStreetMap Nominatim**: No key required (free geocoding API)

---

## ✅ All APIs Are Correct!

All API integrations correctly use environment variables. No hardcoded keys found.

