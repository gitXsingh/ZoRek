# ZoRek Bot - Handler Scripts Documentation

## Overview

ZoRek is an entertainment chatbot built for Zoho SalesIQ that provides personalized recommendations for movies, books, games, food, and music, along with event booking capabilities. The bot consists of four Deluge handler scripts that work together to create a seamless conversational experience.

## Handler Scripts

### 1. TriggerHandler.deluge
**Purpose:** Initial greeting when a visitor starts a chat session.

**Features:**
- Displays welcome message introducing ZoRek as entertainment assistant
- Presents main menu options: Suggest Something, Book an Event, My Pick Combo, Connect to Spotify, Connect with human
- Simple, clean implementation with immediate response

**Integration:**
- First point of contact for all visitors
- Sets the tone for the conversation
- Provides clear navigation options

---

### 2. MessageHandler.deluge
**Purpose:** Routes user messages to appropriate contexts and handles card selections.

**Features:**
- **Message Routing:** Routes user input to correct context handlers
  - "Suggest Something" → suggest_context
  - "Book an Event" → event_context
  - "My Pick Combo" → combo_context
  - "Connect to Spotify" → provides OAuth URL
  - "Connect with human" → forwards to operator

- **Card Selection Handling:** Detects numeric input (1-10) as card selection
  - Retrieves stored card URLs from visitor session
  - Provides direct links to selected items
  - Graceful fallback if session data unavailable

- **Empty Message Handling:** Handles empty or unclear messages with helpful prompts

- **City Options:** Comprehensive list of 200+ Indian cities for event booking

**Integration:**
- Acts as central router for all user interactions
- Integrates with Zoho SalesIQ visitor session for card URL storage
- Seamlessly connects to backend API endpoints via context handlers

---

### 3. ContextHandler.deluge
**Purpose:** Core logic handler that processes user preferences and fetches recommendations.

**Features:**

#### Suggest Something Context
- **Category Selection:** Movies, Books, Games, Food, Music, Surprise Me
- **Preference Collection:**
  - Movies: Genre, IMDB rating, release year
  - Books: Subject/genre
  - Games: Keyword/type
  - Food: Dietary preferences
  - Music: Song style/type
- **API Integration:** Calls backend `/suggest_cards` endpoint
- **Card Display:** Formats recommendations as numbered cards with images and URLs
- **Session Storage:** Stores card URLs for later retrieval
- **Fallback Handling:** Provides fallback cards if API fails

#### Book an Event Context
- **Event Type Selection:** Movies (Now Playing), Concerts, Talkshow, Theater, Sports, Find Events
- **City Selection:** 200+ Indian cities supported
- **API Integration:** Calls backend `/events_cards` endpoint with category and city
- **Event Cards:** Displays events with booking links
- **Fallback Options:** Google search and BookMyShow links if API unavailable

#### My Pick Combo Context
- **Multi-Preference Collection:**
  - Mood selection (Happy, Chill, Romantic, Energetic, Mystery, Adventurous)
  - Movie genre preference
  - Song style preference
  - Diet preference
- **Combo Generation:** Creates personalized entertainment combo
- **API Integration:** Calls backend `/recommendations` endpoint
- **Multi-Card Display:** Shows movie, music, and food recommendations together
- **Fallback Combo:** Provides basic combo if API fails

**Integration:**
- Backend API calls via `invokeurl` to `https://zorek.onrender.com`
- Zoho SalesIQ visitor session for storing card URLs
- Portal name extraction for session management
- Error handling with try-catch blocks
- Fallback mechanisms for API failures

---

### 4. FailureHandler.deluge
**Purpose:** Handles errors and provides user-friendly error messages.

**Features:**
- **Error Code Handling:**
  - 1001: Offline status
  - 1002: All agents busy
  - 1003: Operator unavailable
  - 1005: Reply too long
  - 1007: Execution error
- **User-Friendly Messages:** Clear, helpful error messages
- **Recovery Options:** Always provides suggestions for next steps
- **Generic Fallback:** Handles unknown errors gracefully

**Integration:**
- Integrates with Zoho SalesIQ error system
- Maintains conversation flow even during errors
- Provides clear recovery paths for users

---

## Key Features Coverage

### 1. Suggest Something ✅
- **Coverage:** Fully implemented
- **Categories:** Movies, Books, Games, Food, Music
- **Preference Collection:** Category-specific preferences collected before API calls
- **Third-Party Integration:** OMDb, TMDB, Google Books, Spoonacular, CheapShark, iTunes APIs
- **Display Format:** Numbered cards with images, titles, subtitles, and direct links

### 2. Book an Event ✅
- **Coverage:** Fully implemented
- **Event Types:** Movies, Concerts, Talkshow, Theater, Sports
- **Location-Based:** City selection with 200+ Indian cities
- **Third-Party Integration:** SeatGeek, BookMyShow, Google Search
- **Action Items:** Direct booking links and event search options

### 3. My Pick Combo ✅
- **Coverage:** Custom creative feature
- **Multi-Modal Recommendations:** Combines movie, music, and food
- **Mood-Based:** Personalization based on user mood
- **Integration:** Multiple APIs combined for comprehensive recommendations

### 4. OAuth 2.0 Integration ✅
- **Coverage:** Spotify OAuth implemented
- **Implementation:** MessageHandler provides OAuth start URL
- **Backend Integration:** Connects to `/oauth/spotify/start` endpoint
- **User Experience:** Seamless connection flow with clear instructions

### 5. Data Collection & Logging ✅
- **Coverage:** Backend handles Google Sheets logging
- **Integration:** All user interactions logged via Sheet.best API
- **Data Points:** Category, preferences, city, results count, timestamps

---

## Integration Architecture

### Minimal Integration Approach

The bot uses a **minimal integration pattern** that separates concerns:

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

### Integration Points

```
User → Zoho SalesIQ → Deluge Handlers → Backend API → Third-Party APIs
                ↓
         Session Storage
                ↓
         Card URL Retrieval
```

### Session Management

- **Storage:** Card URLs stored in Zoho SalesIQ visitor session
- **Key:** `zorek_cards` map with numbered keys (1-10)
- **Retrieval:** MessageHandler retrieves URLs when user selects a number
- **Portal Name:** Extracted from request for session access

### API Communication

- **Method:** HTTP POST via `invokeurl`
- **Endpoints:**
  - `/suggest_cards` - For suggestions
  - `/events_cards` - For events
  - `/recommendations` - For combos
- **Payload Format:** JSON with category and preferences
- **Response Format:** Multiple product format with elements array
- **Error Handling:** Try-catch blocks with fallback cards

---

## Requirements Coverage

### Core Requirements ✅

1. **Suggest Something**
   - ✅ Multiple categories (Movies, Books, Games, Food, Music)
   - ✅ Preference collection before suggestions
   - ✅ Third-party API integration
   - ✅ Card-based display format

2. **Book an Event**
   - ✅ Multiple event types
   - ✅ Location-based search
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

---

## Technical Implementation

### Code Quality

- **Clean Code:** Human-written comments in lowercase
- **Error Handling:** Comprehensive try-catch blocks
- **Fallback Mechanisms:** Graceful degradation on API failures
- **Session Management:** Proper portal name extraction and storage
- **Response Formatting:** Consistent card display format

### Best Practices

- Follows Zoho SalesIQ demo bot patterns
- Uses `replies` collection for card displays
- Implements `input` with select type for numbered options
- Proper context chaining for multi-step flows
- Safe answer extraction with null checks

### Performance

- Minimal API calls (only when needed)
- Efficient session storage
- Fallback cards for quick responses
- Optimized card processing loops

---

## File Structure

```
ZoRek_bot.zip
├── TriggerHandler.deluge      (8 lines)   - Initial greeting
├── MessageHandler.deluge      (184 lines) - Message routing
├── ContextHandler.deluge      (1548 lines) - Core logic
└── FailureHandler.deluge      (65 lines)  - Error handling
```

**Total:** ~1,805 lines of clean, commented Deluge code

---

## Setup Instructions

1. **Extract ZoRek_bot.zip**
2. **Access Zoho SalesIQ Bot Builder**
3. **Upload each handler script:**
   - TriggerHandler.deluge → Trigger Handler
   - MessageHandler.deluge → Message Handler
   - ContextHandler.deluge → Context Handler
   - FailureHandler.deluge → Failure Handler
4. **Configure Backend URL:** Ensure `https://zorek.onrender.com` is accessible
5. **Test Each Feature:**
   - Suggest Something (all categories)
   - Book an Event (various cities)
   - My Pick Combo
   - Connect to Spotify
6. **Verify Session Storage:** Test card selection by number

---

## Integration Summary

The ZoRek bot handlers provide a **minimal yet comprehensive** integration:

- **Minimal:** Clean separation between frontend (Deluge) and backend (API)
- **Comprehensive:** Covers all required features plus brownie points
- **Scalable:** Easy to extend with new categories or features
- **Maintainable:** Well-commented, human-readable code
- **Robust:** Error handling and fallback mechanisms throughout

The bot successfully integrates multiple third-party APIs, OAuth 2.0 authentication, and data logging while maintaining a clean, conversational user experience.

