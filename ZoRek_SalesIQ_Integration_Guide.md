# ZoRek - Zoho SalesIQ Integration Guide

This guide explains how to integrate ZoRek with Zoho SalesIQ using the codeless bot builder and widget system.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Plug Configuration](#plug-configuration)
3. [Widget Configuration](#widget-configuration)
4. [API Endpoints](#api-endpoints)
5. [Input/Output Schemas](#inputoutput-schemas)
6. [Step-by-Step Setup](#step-by-step-setup)
7. [Example Flows](#example-flows)
8. [Troubleshooting](#troubleshooting)

## 🎯 Overview

ZoRek provides three main SalesIQ plugs:

1. **Plug 1: Suggest Something** → `/suggest_cards`
2. **Plug 2: Book an Event** → `/events_cards`
3. **Plug 3: My Pick (Creative)** → `/recommendations`

Additionally, ZoRek provides a **Widget Detail** endpoint for operator panels.

## 🔌 Plug Configuration

### Plug 1: Suggest Something

**Endpoint**: `POST https://zorek.onrender.com/suggest_cards`

**Purpose**: Get recommendations for Movies, Books, Games, Food, or Music.

**Input Schema**:
```json
{
  "category": "Movies|Books|Games|Food|Music",
  "prefs": {
    "genre": "Drama",           // For Movies
    "minImdb": 7.0,             // For Movies (optional)
    "year": "2019",             // For Movies (optional)
    "subject": "Fiction",       // For Books
    "keyword": "racing",        // For Games
    "songType": "Pop",          // For Music
    "diet": "Veg"               // For Food
  }
}
```

**Output Schema**:
```json
{
  "cards": [
    {
      "title": "Inception (2010)",
      "imageUrl": "https://image.tmdb.org/t/p/w500/xyz.jpg",
      "description": "⭐ 8.8",
      "action": {
        "label": "View",
        "url": "https://www.imdb.com/title/tt1375666/"
      }
    }
  ]
}
```

**SalesIQ Plug Setup**:
1. Go to SalesIQ → Bots → Create Bot
2. Add a new Plug
3. Set **Method**: POST
4. Set **URL**: `https://zorek.onrender.com/suggest_cards`
5. Set **Headers**: `Content-Type: application/json`
6. Set **Body**: Use the input schema above
7. Map response fields:
   - `cards[].title` → Card Title
   - `cards[].imageUrl` → Card Image
   - `cards[].description` → Card Description
   - `cards[].action.url` → Card Link

### Plug 2: Book an Event

**Endpoint**: `POST https://zorek.onrender.com/events_cards`

**Purpose**: Find events (Concerts, Talkshows, Theater, Sports, Movies) near a city.

**Input Schema**:
```json
{
  "category": "Concerts|Talkshow|Theater|Sports|Movies|Find events",
  "city": "Mumbai"
}
```

**Output Schema**:
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

**SalesIQ Plug Setup**:
1. Go to SalesIQ → Bots → Create Bot
2. Add a new Plug
3. Set **Method**: POST
4. Set **URL**: `https://zorek.onrender.com/events_cards`
5. Set **Headers**: `Content-Type: application/json`
6. Set **Body**: Use the input schema above
7. Map response fields:
   - `cards[].title` → Card Title
   - `cards[].description` → Card Description
   - `cards[].action.url` → Card Link

### Plug 3: My Pick (Creative)

**Endpoint**: `POST https://zorek.onrender.com/recommendations`

**Purpose**: Get a creative combination of Movie + Song + Food based on mood and preferences.

**Input Schema**:
```json
{
  "mood": "Happy|Sad|Romantic|Adventurous|Chill|Scared|Excited|Bored|Curious|Nostalgic",
  "movieGenre": "Action|Adventure|Comedy|Drama|Horror|Romance|Sci-Fi|Thriller|...",
  "songType": "Pop|Rock|Hip-hop|Lo-fi|Jazz|Classical|EDM|Country|R&B|Indie|Metal|K-Pop",
  "diet": "Veg|Non-veg"
}
```

**Output Schema**:
```json
{
  "movie": {
    "text": "🎬 Inception (2010)",
    "url": "https://www.imdb.com/title/tt1375666/",
    "image": "https://image.tmdb.org/t/p/w500/xyz.jpg"
  },
  "song": {
    "text": "🎵 Bad Guy — Billie Eilish",
    "url": "https://open.spotify.com/track/...",
    "image": "https://i.scdn.co/image/..."
  },
  "food": {
    "text": "🍕 Caprese Salad",
    "url": "https://www.foodista.com/recipe/...",
    "image": "https://img.spoonacular.com/recipes/..."
  },
  "inputs": {
    "mood": "Happy",
    "movieGenre": "Action",
    "songType": "Pop",
    "diet": "Veg"
  }
}
```

**SalesIQ Plug Setup**:
1. Go to SalesIQ → Bots → Create Bot
2. Add a new Plug
3. Set **Method**: POST
4. Set **URL**: `https://zorek.onrender.com/recommendations`
5. Set **Headers**: `Content-Type: application/json`
6. Set **Body**: Use the input schema above
7. Display response:
   - Show `movie.text`, `song.text`, `food.text`
   - Add links using `movie.url`, `song.url`, `food.url`
   - Optionally show images using `movie.image`, `song.image`, `food.image`

## 🎨 Widget Configuration

### Operator Widget

**Endpoint**: `GET https://zorek.onrender.com/widget_detail?email=visitor@example.com`

**Purpose**: Display visitor data in the operator chat window.

**Response Schema**:
```json
{
  "email": "visitor@example.com",
  "lastChoice": "Movies",
  "lastGenre": "Action",
  "lastSuggestion": "Inception (2010)",
  "timestamp": "2025-01-15T10:30:00",
  "interactionCount": 1
}
```

**SalesIQ Widget Setup**:
1. Go to SalesIQ → Settings → Widgets
2. Create a new Widget
3. Set **Type**: Widget Detail
4. Set **URL**: `https://zorek.onrender.com/widget_detail`
5. Set **Method**: GET
6. Pass `email` as query parameter (SalesIQ provides visitor email)
7. Map response fields to widget sections:
   - `lastChoice` → Metric Section
   - `lastGenre` → Metric Section
   - `lastSuggestion` → Listing Section
   - `timestamp` → Fieldset Section

## 📊 Input/Output Schemas

### Movies Input
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

### Books Input
```json
{
  "category": "Books",
  "prefs": {
    "subject": "Fiction",
    "lang": "en"
  }
}
```

### Games Input
```json
{
  "category": "Games",
  "prefs": {
    "keyword": "racing"
  }
}
```

### Music Input
```json
{
  "category": "Music",
  "prefs": {
    "songType": "Pop"
  }
}
```

### Food Input
```json
{
  "category": "Food",
  "prefs": {
    "diet": "Veg"
  }
}
```

### Events Input
```json
{
  "category": "Concerts",
  "city": "Mumbai"
}
```

## 🔧 Step-by-Step Setup

### 1. Configure Environment Variables

Ensure your ZoRek instance has all required API keys set in environment variables.

### 2. Test Endpoints

Test each endpoint using curl or Postman:

```bash
# Test Suggest Cards
curl -X POST https://zorek.onrender.com/suggest_cards \
  -H "Content-Type: application/json" \
  -d '{"category":"Movies","prefs":{"genre":"Drama","minImdb":7.0}}'

# Test Events Cards
curl -X POST https://zorek.onrender.com/events_cards \
  -H "Content-Type: application/json" \
  -d '{"category":"Concerts","city":"Mumbai"}'

# Test Recommendations
curl -X POST https://zorek.onrender.com/recommendations \
  -H "Content-Type: application/json" \
  -d '{"mood":"Happy","movieGenre":"Action","songType":"Pop","diet":"Veg"}'
```

### 3. Create SalesIQ Bot

1. Log in to Zoho SalesIQ
2. Go to **Bots** → **Create Bot**
3. Choose **Codeless Bot Builder**
4. Add conversation flow

### 4. Add Plugs

For each plug:
1. Click **Add Plug**
2. Configure HTTP request
3. Set URL, Method, Headers, Body
4. Map response fields to bot messages
5. Test the plug

### 5. Configure Widget

1. Go to **Settings** → **Widgets**
2. Create new widget
3. Set widget type to **Widget Detail**
4. Configure URL and parameters
5. Map response fields to widget sections

## 💡 Example Flows

### Example 1: Movie Suggestion Flow

**User**: "Suggest a drama movie"

**Bot Flow**:
1. Bot asks: "What minimum IMDb rating? (e.g., 7.0)"
2. User: "7.0"
3. Bot calls Plug 1: `/suggest_cards` with `{"category":"Movies","prefs":{"genre":"Drama","minImdb":7.0}}`
4. Bot displays cards with movie recommendations
5. User clicks on a card → Opens IMDb page

### Example 2: Event Booking Flow

**User**: "Find concerts near Mumbai"

**Bot Flow**:
1. Bot calls Plug 2: `/events_cards` with `{"category":"Concerts","city":"Mumbai"}`
2. Bot displays cards with concert events
3. User clicks on a card → Opens ticket booking page

### Example 3: My Pick Flow

**User**: "Give me a happy combo"

**Bot Flow**:
1. Bot asks: "What movie genre?"
2. User: "Action"
3. Bot asks: "What song type?"
4. User: "Pop"
5. Bot asks: "Veg or Non-veg?"
6. User: "Veg"
7. Bot calls Plug 3: `/recommendations` with `{"mood":"Happy","movieGenre":"Action","songType":"Pop","diet":"Veg"}`
8. Bot displays movie + song + food with links

## 🐛 Troubleshooting

### Plug Not Working

**Issue**: Plug returns error
**Solution**:
- Check that API keys are set correctly
- Verify endpoint URL is correct
- Check request body format
- Test endpoint directly with curl

### CORS Errors

**Issue**: CORS error when calling from SalesIQ
**Solution**:
- Verify CORS is configured in `app.py`
- Check that your SalesIQ domain is allowed
- Ensure `Flask-CORS` is installed

### Widget Not Displaying

**Issue**: Widget not showing data
**Solution**:
- Verify widget URL is correct
- Check that email parameter is passed
- Test endpoint directly with curl
- Check widget configuration in SalesIQ

### API Keys Not Working

**Issue**: API returns errors
**Solution**:
- Verify API keys are set in environment variables
- Check that API keys are valid
- Ensure API keys have proper permissions
- Test APIs directly

## 📞 Support

For issues and questions:
1. Check the [README.md](./README.md) for general documentation
2. Test endpoints using curl or Postman
3. Check `/health_check` endpoint for API status
4. Open an issue on GitHub

## 🔗 Links

- **ZoRek Live**: https://zorek.onrender.com
- **Health Check**: https://zorek.onrender.com/health_check
- **GitHub**: https://github.com/gitXsingh/ZoRek
- **Zoho SalesIQ**: https://www.zoho.com/salesiq/

## 📝 Notes

- All endpoints return JSON
- All endpoints support UTF-8 encoding
- All endpoints return proper error responses (400, 500)
- All endpoints log interactions to Google Sheets
- CORS is configured for Zoho SalesIQ domains
- OAuth 2.0 is used for Spotify authentication

## 🎯 Best Practices

1. **Error Handling**: Always handle errors gracefully
2. **Logging**: Log all interactions for analytics
3. **Security**: Keep API keys secure in environment variables
4. **Testing**: Test all endpoints before deploying
5. **Documentation**: Keep documentation up to date

## 📊 Response Time

- Typical response time: 1-3 seconds
- Timeout: 20 seconds for AI commentary, 10 seconds for other endpoints
- Retry: Not implemented (handle in SalesIQ bot)

## 🔒 Security

- All API keys are stored in environment variables
- CORS is configured for specific domains
- OAuth 2.0 is used for Spotify
- All endpoints validate input
- Error messages don't expose sensitive information

---

**Last Updated**: January 2025
**Version**: 1.0.0

