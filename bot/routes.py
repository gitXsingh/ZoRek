"""
Bot Routes - Zoho SalesIQ Bot Endpoints
ONLY 3 endpoints: /suggest_cards, /events_cards, /recommendations
"""

from flask import request, jsonify
import datetime
import traceback
import requests
import sys
import logging
from typing import Dict, List

# Configure logging for Render (ensures logs are visible)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ====== UTILITY HELPERS ======

def safe_get(obj: dict, key: str, default=None):
    """Safely get value from dict with default fallback"""
    if not obj:
        return default
    return obj.get(key, default) or default


def normalize(value: str) -> str:
    """Normalize string values - trim and lowercase"""
    if not value:
        return ""
    return str(value).strip().lower()


def make_card(title: str, desc: str = "", img: str = None, label: str = "View", url: str = None, card_id: str = None) -> dict:
    """Create a standardized card object in Zoho Multiple Product format"""
    card_id = card_id or title.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(":", "")[:50]
    # Ensure URL is always valid - use fallback if None or empty
    valid_url = url if url and str(url).strip() and str(url).lower() != "null" else "https://zorek.onrender.com"
    # Ensure image is valid or empty string (not None)
    valid_image = str(img) if img and str(img).strip() and str(img).lower() != "null" else ""
    return {
        "id": card_id,
        "title": str(title) if title else "No Title",
        "subtitle": str(desc) if desc else "",
        "image": valid_image,
        "actions": [
            {
                "label": str(label) if label else "Open",
                "name": card_id + "_action",
                "type": "url",
                "link": str(valid_url)
            }
        ]
    }


def fallback_empty_card() -> dict:
    """Return a fallback card when no data is available"""
    return make_card(
        title="No Data",
        desc="Try again later",
        img=None,
        label="Open",
        url=None,
        card_id="no_data"
    )


def multiple_product_payload(text: str, cards: List[dict]) -> dict:
    """Wrap cards in Zoho multiple-product payload while keeping backward compatibility"""
    safe_cards = cards or [fallback_empty_card()]
    safe_text = text or "Here are some picks for you:"
    return {
        "type": "multiple-product",
        "text": safe_text,
        "elements": safe_cards,
        # Keep legacy key so older handlers (or logging) can still access cards
        "cards": safe_cards
    }


FALLBACK_SUGGESTIONS = {
    "movies": [
        {"title": "Inception (2010)", "desc": "Sci-Fi · IMDb 8.8", "img": "https://image.tmdb.org/t/p/w500/qmDpIHrmpJINaRKAfWQfftjCdyi.jpg", "label": "Watch Now", "url": "https://www.imdb.com/title/tt1375666/"},
        {"title": "The Dark Knight (2008)", "desc": "Action · IMDb 9.0", "img": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "label": "Watch Now", "url": "https://www.imdb.com/title/tt0468569/"},
        {"title": "Interstellar (2014)", "desc": "Adventure · IMDb 8.7", "img": "https://image.tmdb.org/t/p/w500/rAiYTfKGqDCRIIqo664sY9XZIvQ.jpg", "label": "Watch Now", "url": "https://www.imdb.com/title/tt0816692/"}
    ],
    "books": [
        {"title": "Atomic Habits", "desc": "James Clear · Productivity", "img": "https://images-na.ssl-images-amazon.com/images/I/81bGKUa1e0L.jpg", "label": "Read More", "url": "https://www.goodreads.com/book/show/40121378-atomic-habits"},
        {"title": "Project Hail Mary", "desc": "Andy Weir · Sci-Fi", "img": "https://images-na.ssl-images-amazon.com/images/I/91xPRev9DwL.jpg", "label": "Read More", "url": "https://www.goodreads.com/book/show/54493401-project-hail-mary"},
        {"title": "The Midnight Library", "desc": "Matt Haig · Fiction", "img": "https://images-na.ssl-images-amazon.com/images/I/81Bf46mx63L.jpg", "label": "Read More", "url": "https://www.goodreads.com/book/show/52578297-the-midnight-library"}
    ],
    "games": [
        {"title": "The Witcher 3: Wild Hunt", "desc": "RPG · PC / Console", "img": "https://cdn.cloudflare.steamstatic.com/steam/apps/292030/header.jpg?t=1668104445", "label": "View Game", "url": "https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/"},
        {"title": "Hades", "desc": "Action Roguelike · PC / Switch", "img": "https://cdn.cloudflare.steamstatic.com/steam/apps/1145360/header.jpg", "label": "View Game", "url": "https://store.steampowered.com/app/1145360/Hades/"},
        {"title": "Forza Horizon 5", "desc": "Racing · Xbox / PC", "img": "https://cdn.cloudflare.steamstatic.com/steam/apps/1551360/header.jpg", "label": "View Game", "url": "https://store.steampowered.com/app/1551360/Forza_Horizon_5/"}
    ],
    "music": [
        {"title": "As It Was – Harry Styles", "desc": "Pop · 2022", "img": "https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/2a/19/fb/2a19fb85-2f70-9e44-f2a9-82abe679b88e/886449990061.jpg/100x100bb.jpg", "label": "Listen", "url": "https://open.spotify.com/track/4LRPiXqCikLlN15c3yImP7"},
        {"title": "Blinding Lights – The Weeknd", "desc": "Pop · 2020", "img": "https://i.scdn.co/image/ab67616d0000b2734c2fd0f5b4c5f1318c3aaf36", "label": "Listen", "url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"},
        {"title": "Levitating – Dua Lipa", "desc": "Pop · 2020", "img": "https://is4-ssl.mzstatic.com/image/thumb/Music115/v4/00/21/3d/00213d3b-2ddd-b4db-0fd2-2ed07e675985/190295186869.jpg/100x100bb.jpg", "label": "Listen", "url": "https://open.spotify.com/track/463CkQjx2Zk1yXoBuierM9"}
    ],
    "food": [
        {"title": "Mediterranean Buddha Bowl", "desc": "Veg · 30 min meal", "img": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=600&q=80", "label": "View Recipe", "url": "https://www.loveandlemons.com/buddha-bowl/"},
        {"title": "Spicy Ramen Upgrade", "desc": "Comfort · Quick fix", "img": "https://images.unsplash.com/photo-1504753793650-d4a2b783c15e?auto=format&fit=crop&w=600&q=80", "label": "View Recipe", "url": "https://www.bonappetit.com/recipe/spicy-miso-ramen"},
        {"title": "Berry Yogurt Parfait", "desc": "Breakfast · Fresh", "img": "https://images.unsplash.com/photo-1470337458703-46ad1756a187?auto=format&fit=crop&w=600&q=80", "label": "View Recipe", "url": "https://www.foodnetwork.com/recipes/berry-parfait-recipe"}
    ]
}


FALLBACK_MOVIE_RECO = {
    "text": "🎬 Inception — Mind-bending sci-fi classic",
    "url": "https://www.imdb.com/title/tt1375666/",
    "image": "https://image.tmdb.org/t/p/w500/qmDpIHrmpJINaRKAfWQfftjCdyi.jpg",
    "poster": "https://image.tmdb.org/t/p/w500/qmDpIHrmpJINaRKAfWQfftjCdyi.jpg"
}

FALLBACK_SONG_RECO = {
    "text": "🎵 Blinding Lights — The Weeknd",
    "url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
    "image": "https://i.scdn.co/image/ab67616d0000b2734c2fd0f5b4c5f1318c3aaf36",
    "source": "Spotify"
}

FALLBACK_FOOD_RECO = {
    "text": "🍕 Veggie Burrito Bowl — Fresh & filling",
    "url": "https://www.loveandlemons.com/vegetarian-burrito-bowl/",
    "image": "https://images.unsplash.com/photo-1478145046317-39f10e56b5e9?auto=format&fit=crop&w=600&q=80"
}


def category_fallback_cards(category: str) -> List[dict]:
    entries = FALLBACK_SUGGESTIONS.get(category.lower())
    if not entries:
        return [fallback_empty_card()]
    return [make_card(**entry) for entry in entries]


def fallback_movie_recommendation() -> dict:
    return {
        "text": FALLBACK_MOVIE_RECO["text"],
        "url": FALLBACK_MOVIE_RECO["url"],
        "image": FALLBACK_MOVIE_RECO["image"],
        "poster": FALLBACK_MOVIE_RECO["poster"]
    }


def fallback_song_recommendation() -> dict:
    return {
        "text": FALLBACK_SONG_RECO["text"],
        "url": FALLBACK_SONG_RECO["url"],
        "image": FALLBACK_SONG_RECO["image"],
        "source": FALLBACK_SONG_RECO["source"]
    }


def fallback_food_recommendation() -> dict:
    return {
        "text": FALLBACK_FOOD_RECO["text"],
        "url": FALLBACK_FOOD_RECO["url"],
        "image": FALLBACK_FOOD_RECO["image"]
    }


# ====== MAIN ENDPOINT REGISTRATION ======

def create_bot_routes(
    app,
    # API functions
    search_movies_with_filters,
    suggest_books_with_links,
    suggest_games_with_links,
    suggest_music_with_links,
    get_food_recommendation_with_url,
    get_movie_recommendation_with_url,
    get_song_recommendation_with_url,
    events_from_seatgeek,
    fallback_event_links,
    geocode_city,
    fetch_trending_movies,  # Trending movies fallback function
    # Configuration
    SHEET_BEST_URL: str,
    TMDB_KEY: str,
    SEATGEEK_CLIENT_ID: str
):
    """
    Register ONLY the 3 required endpoints for Zoho SalesIQ Script Bot.
    """
    
    @app.route('/suggest_cards', methods=['POST'])
    def suggest_cards():
        """
        Endpoint 1: Suggest Something
        Input: {"category": "string", "prefs": {}}
        Output: {"cards": [{title, description, imageUrl, action: {label, url}}]}
        """
        # Log incoming request (both print and logger for Render visibility)
        logger.info("="*60)
        logger.info("🔵 [REQUEST] POST /suggest_cards")
        logger.info(f"Time: {datetime.datetime.utcnow().isoformat()}")
        logger.info(f"Remote: {request.remote_addr}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Raw data: {request.get_data(as_text=True)[:200]}")
        
        print("\n" + "="*60)
        print("🔵 [REQUEST] POST /suggest_cards")
        print(f"   Time: {datetime.datetime.utcnow().isoformat()}")
        print(f"   Remote: {request.remote_addr}")
        print(f"   Content-Type: {request.content_type}")
        
        try:
            # Try to get JSON data - be more flexible with content types
            data = None
            if request.is_json:
                data = request.get_json(force=True)
            elif request.content_type and 'application/json' in request.content_type:
                data = request.get_json(force=True)
            elif request.data:
                try:
                    import json
                    data = json.loads(request.get_data(as_text=True))
                except:
                    pass
            
            # If still no data, try form data
            if not data and request.form:
                data = request.form.to_dict()
            
            logger.info(f"Parsed data: {data}")
            print(f"   📥 Parsed data: {data}")
            
            if not data:
                logger.error("❌ ERROR: No data received or couldn't parse")
                print("   ❌ ERROR: No data received or couldn't parse")
                return jsonify(multiple_product_payload("Unable to read request payload.", [fallback_empty_card()])), 400
            
            category = normalize(safe_get(data, "category", ""))
            prefs_raw = safe_get(data, "prefs", {}) or {}
            
            # Handle prefs - could be dict or JSON string
            prefs = {}
            if isinstance(prefs_raw, dict):
                prefs = prefs_raw
            elif isinstance(prefs_raw, str):
                try:
                    import json
                    prefs = json.loads(prefs_raw) if prefs_raw.strip() else {}
                except Exception as e:
                    logger.warning(f"Could not parse prefs as JSON: {prefs_raw}, error: {e}")
                    prefs = {}
            
            logger.info(f"Input: category='{category}', prefs={prefs}")
            print(f"   📥 Input: category='{category}', prefs={prefs}")
            
            if not category:
                logger.error("❌ ERROR: No category provided")
                print("   ❌ ERROR: No category provided")
                return jsonify(multiple_product_payload("Please provide a category.", [fallback_empty_card()])), 400
            
            # Get items based on category
            items = []
            try:
                if category == "movies":
                    genre = normalize(safe_get(prefs, "genre", ""))
                    min_imdb_raw = safe_get(prefs, "minImdb", "") or ""
                    # Handle string values like "7.0" or "7.0+" from Deluge
                    try:
                        min_imdb_str = str(min_imdb_raw).replace("+", "").strip()
                        min_imdb = float(min_imdb_str) if min_imdb_str else 0.0
                    except (ValueError, TypeError):
                        min_imdb = 0.0
                    year = normalize(safe_get(prefs, "year", ""))
                    logger.info(f"Fetching movies: genre='{genre}', min_imdb={min_imdb}, year='{year}'")
                    print(f"   🎬 Fetching movies: genre='{genre}', min_imdb={min_imdb}, year='{year}'")
                    
                    # If no genre specified, use "popular" to get trending movies
                    if not genre:
                        genre = "popular"
                        logger.info("No genre specified, using 'popular' to fetch trending movies")
                        print(f"   🎬 No genre specified, using 'popular' for trending movies")
                    
                    items = search_movies_with_filters(genre, min_imdb, year)
                    logger.info(f"Movies API returned {len(items)} items")
                    print(f"   🎬 Movies API returned {len(items)} items")
                    
                    # Filter out error messages and items without valid URLs
                    valid_items = []
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        text = it.get("text", "")
                        url = it.get("url")
                        # Skip error messages and items without valid URLs
                        if not text or "No movies matched" in text or "⚠️" in text or "error" in text.lower():
                            continue
                        if not url or not str(url).strip() or str(url).lower() == "null":
                            continue
                        valid_items.append(it)
                    
                    items = valid_items
                    logger.info(f"After filtering errors: {len(items)} valid items")
                    print(f"   🎬 After filtering errors: {len(items)} valid items")
                    
                    # If still no items, try with trending movies as fallback
                    if not items and TMDB_KEY:
                        logger.info("No items after filtering, trying trending movies fallback")
                        print(f"   🎬 No valid items, trying trending movies fallback...")
                        try:
                            trending = fetch_trending_movies(limit=5)
                            if trending:
                                items = trending
                                logger.info(f"Trending movies fallback returned {len(items)} items")
                                print(f"   🎬 Trending movies fallback returned {len(items)} items")
                        except Exception as e:
                            logger.warning(f"Trending movies fallback failed: {e}")
                            items = []
                elif category == "books":
                    subject = normalize(safe_get(prefs, "subject", ""))
                    lang = normalize(safe_get(prefs, "lang", ""))
                    logger.info(f"Fetching books: subject='{subject}', lang='{lang}'")
                    print(f"   📚 Fetching books: subject='{subject}', lang='{lang}'")
                    items = suggest_books_with_links(subject, lang)
                    logger.info(f"Books API returned {len(items)} items")
                    print(f"   📚 Books API returned {len(items)} items")
                elif category == "games":
                    keyword = normalize(safe_get(prefs, "keyword", ""))
                    logger.info(f"Fetching games: keyword='{keyword}'")
                    print(f"   🎮 Fetching games: keyword='{keyword}'")
                    items = suggest_games_with_links(keyword)
                    logger.info(f"Games API returned {len(items)} items")
                    print(f"   🎮 Games API returned {len(items)} items")
                elif category == "music":
                    keyword = normalize(safe_get(prefs, "songType") or safe_get(prefs, "keyword") or safe_get(prefs, "query", ""))
                    logger.info(f"Fetching music: keyword='{keyword}'")
                    print(f"   🎵 Fetching music: keyword='{keyword}'")
                    items = suggest_music_with_links(keyword)
                    logger.info(f"Music API returned {len(items)} items")
                    print(f"   🎵 Music API returned {len(items)} items")
                elif category == "food":
                    diet = normalize(safe_get(prefs, "diet", ""))
                    logger.info(f"Fetching food: diet='{diet}'")
                    print(f"   🍕 Fetching food: diet='{diet}'")
                    food_item = get_food_recommendation_with_url(diet)
                    items = [food_item] if food_item else []
                    logger.info(f"Food API returned {len(items)} items")
                    print(f"   🍕 Food API returned {len(items)} items")
                else:
                    logger.warning(f"Unknown category: {category}")
                    print(f"   ⚠️ Unknown category: {category}")
                    items = []
            except Exception as e:
                error_msg = traceback.format_exc()
                logger.error(f"⚠️ Error fetching items for {category}: {str(e)}")
                logger.error(error_msg)
                print(f"⚠️ Error fetching items for {category}: {e}")
                print(f"   Traceback: {error_msg[:200]}")
                items = []
            
            # Transform to cards format
            cards = []
            logger.info(f"Transforming {len(items)} items to cards")
            print(f"   🔄 Transforming {len(items)} items to cards")
            
            for it in (items or [])[:10]:
                if not isinstance(it, dict):
                    logger.warning(f"Skipping non-dict item: {type(it)}")
                    continue
                
                text = safe_get(it, "text", "")
                url = safe_get(it, "url")
                image = safe_get(it, "image") or safe_get(it, "poster")
                
                # Skip items without valid text
                if not text or not text.strip():
                    continue
                
                # Clean title from text
                title = text.replace("🎬", "").replace("📚", "").replace("🎮", "").replace("🎵", "").replace("🍕", "").strip()
                if " — " in title:
                    title = title.split(" — ")[0].strip()
                if "—" in title:
                    title = title.split("—")[0].strip()
                
                # Extract description - better parsing
                desc = category.title()
                if "⭐" in text:
                    rating_part = text.split("⭐")[1].strip() if "⭐" in text else ""
                    if rating_part:
                        desc = rating_part.split("—")[0].strip() if "—" in rating_part else rating_part[:50]
                elif "·" in text:
                    desc = text.split("·")[1].strip()[:100] if "·" in text else desc
                
                # Set action label based on category
                action_label = "View"
                if category == "movies":
                    action_label = "Watch Now"
                elif category == "books":
                    action_label = "Read More"
                elif category == "games":
                    action_label = "Buy Game"
                elif category == "music":
                    action_label = "Listen"
                elif category == "food":
                    action_label = "View Recipe"
                
                # Ensure URL is valid - use default if not provided
                valid_url = url if url and str(url).strip() and str(url).lower() not in ["null", "none"] else None
                # Ensure image is valid
                valid_image = str(image) if image and str(image).strip() and str(image).lower() != "null" else None
                
                card = make_card(
                    title=title[:100] if title else "Unknown",
                    desc=desc[:200] if desc else category.title(),
                    img=valid_image,
                    label=action_label,
                    url=valid_url
                )
                cards.append(card)
                logger.info(f"Created card: {card.get('title', 'Unknown')[:50]} - URL: {bool(card.get('actions', [{}])[0].get('link'))}")
            
            logger.info(f"Created {len(cards)} cards from {len(items)} items")
            print(f"   ✅ Created {len(cards)} cards from {len(items)} items")
            
            # Ensure cards array is never empty
            if not cards:
                cards = category_fallback_cards(category)
            
            logger.info(f"✅ Output: {len(cards)} cards generated")
            print(f"   ✅ Output: {len(cards)} cards generated")
            print("="*60 + "\n")
            logger.info("="*60)
            
            # Log to Google Sheet - Match all columns
            try:
                if SHEET_BEST_URL:
                    # Extract preferences for logging
                    genre = normalize(safe_get(prefs, "genre", ""))
                    mood = normalize(safe_get(prefs, "mood", ""))
                    
                    # Get first few suggestions from cards
                    suggestions_list = [c.get("title", "")[:50] for c in cards[:3]]
                    
                    log_data = {
                        "Name": "",  # Not available from bot endpoint
                        "Email": "",  # Not available from bot endpoint
                        "Choice": category.title(),
                        "Genre": genre if genre else category.title(),
                        "Mood": mood if mood else "",
                        "Suggestion": ", ".join(suggestions_list) if suggestions_list else "No suggestions",
                        "Endpoint": "suggest_cards",
                        "Category": category.title(),
                        "Preferences": str(prefs) if prefs else "",
                        "City": "",
                        "ResultsCount": len(cards),
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    requests.post(SHEET_BEST_URL, json=log_data, timeout=3)
                    logger.info(f"✅ Logged to sheet: {category.title()} - {len(cards)} results")
            except Exception as e:
                logger.warning(f"⚠️ Logging failed: {e}")
                pass  # Non-blocking
            
            return jsonify(multiple_product_payload(f"Here are some {category.title()} suggestions:", cards))
            
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"❌ EXCEPTION in suggest_cards: {str(e)}")
            logger.error(error_msg)
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ suggest_cards error:", error_msg)
            return jsonify(multiple_product_payload("Unable to fetch suggestions right now.", [fallback_empty_card()])), 400

    @app.route('/events_cards', methods=['POST'])
    def events_cards():
        """
        Endpoint 2: Book an Event
        Input: {"category": "string", "city": "string"}
        Output: {"cards": [{title, description, imageUrl, action: {label, url}}]}
        """
        # Log incoming request (both print and logger for Render visibility)
        logger.info("="*60)
        logger.info("🟢 [REQUEST] POST /events_cards")
        logger.info(f"Time: {datetime.datetime.utcnow().isoformat()}")
        logger.info(f"Remote: {request.remote_addr}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Raw data: {request.get_data(as_text=True)[:200]}")
        
        print("\n" + "="*60)
        print("🟢 [REQUEST] POST /events_cards")
        print(f"   Time: {datetime.datetime.utcnow().isoformat()}")
        print(f"   Remote: {request.remote_addr}")
        print(f"   Content-Type: {request.content_type}")
        
        try:
            # Try to get JSON data - be more flexible with content types
            data = None
            if request.is_json:
                data = request.get_json(force=True)
            elif request.content_type and 'application/json' in request.content_type:
                data = request.get_json(force=True)
            elif request.data:
                try:
                    import json
                    data = json.loads(request.get_data(as_text=True))
                except:
                    pass
            
            # If still no data, try form data
            if not data and request.form:
                data = request.form.to_dict()
            
            logger.info(f"Parsed data: {data}")
            print(f"   📥 Parsed data: {data}")
            
            if not data:
                logger.error("❌ ERROR: No data received or couldn't parse")
                print("   ❌ ERROR: No data received or couldn't parse")
                return jsonify(multiple_product_payload("Unable to read request payload.", [fallback_empty_card()])), 400
            
            category = normalize(safe_get(data, "category", ""))
            city = normalize(safe_get(data, "city", "")) or "mumbai"  # Default fallback
            
            logger.info(f"Input: category='{category}', city='{city}'")
            print(f"   📥 Input: category='{category}', city='{city}'")
            
            if not category:
                logger.error("❌ ERROR: No category provided")
                print("   ❌ ERROR: No category provided")
                return jsonify(multiple_product_payload("Please provide an event category.", [fallback_empty_card()])), 400
            
            # Get events based on category
            results = []
            try:
                if category in ["concerts", "talkshow", "theater", "sports"]:
                    loc = geocode_city(city) if city else None
                    if loc:
                        lat, lon = loc
                        if SEATGEEK_CLIENT_ID:
                            results = events_from_seatgeek(category, lat, lon)
                        if not results:
                            results = fallback_event_links(category, city)
                    else:
                        results = fallback_event_links(category, city)
                elif category in ["find events", "find"]:
                    loc = geocode_city(city) if city else None
                    if loc:
                        lat, lon = loc
                        results = events_from_seatgeek("concerts", lat, lon)
                        if not results:
                            results = fallback_event_links("concerts", city)
                    else:
                        results = fallback_event_links("concerts", city)
                elif category == "movies":
                    if TMDB_KEY:
                        try:
                            data_resp = requests.get(
                                f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_KEY}&language=en-US&page=1",
                                timeout=10
                            ).json()
                            for m in safe_get(data_resp, "results", [])[:10]:
                                title = safe_get(m, "title", "Movie")
                                poster_path = safe_get(m, "poster_path")
                                poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                                dt = safe_get(m, "release_date", "")
                                bms_url = f"https://in.bookmyshow.com/explore/movies-{city}"
                                results.append({
                                    "text": f"🎟️ {title} — {dt}",
                                    "url": bms_url,
                                    "image": poster,
                                    "poster": poster
                                })
                        except Exception:
                            results = fallback_event_links("movies", city)
                    else:
                        results = fallback_event_links("movies", city)
                else:
                    results = fallback_event_links(category, city)
            except Exception as e:
                print(f"⚠️ Error fetching events for {category}: {e}")
                results = fallback_event_links(category, city)
            
            # Transform to cards format
            cards = []
            logger.info(f"Transforming {len(results)} event results to cards")
            print(f"   🔄 Transforming {len(results)} event results to cards")
            
            for it in (results or [])[:10]:
                if not isinstance(it, dict):
                    continue
                
                text = safe_get(it, "text", "")
                url = safe_get(it, "url")
                image = safe_get(it, "image") or safe_get(it, "poster")
                
                # Skip items without valid text
                if not text or not text.strip():
                    continue
                
                title = text.replace("🎟️", "").replace("🔎", "").replace("📅", "").strip()
                if "—" in title:
                    title = title.split("—")[0].strip()
                if " @ " in title:
                    title = title.split(" @ ")[0].strip()
                
                # Better description based on category
                desc = f"Event in {city.title()}"
                if category == "movies":
                    desc = f"Now Playing in {city.title()}"
                elif category == "concerts":
                    desc = f"Concert in {city.title()}"
                elif category == "talkshow":
                    desc = f"Talk Show in {city.title()}"
                elif category == "theater":
                    desc = f"Theater in {city.title()}"
                elif category == "sports":
                    desc = f"Sports Event in {city.title()}"
                
                # Ensure URL is valid - fallback_event_links should always provide URLs
                valid_url = url if url and str(url).strip() and str(url).lower() not in ["null", "none"] else None
                # Ensure image is valid
                valid_image = str(image) if image and str(image).strip() and str(image).lower() != "null" else None
                
                card = make_card(
                    title=title[:100] if title else "Event",
                    desc=desc,
                    img=valid_image,
                    label="Book Tickets",
                    url=valid_url
                )
                cards.append(card)
                action_link = card.get('actions', [{}])[0].get('link', '') if card.get('actions') else ''
                logger.info(f"Created event card: title='{card.get('title', '')[:50]}', url={bool(action_link)}")
                print(f"   ✅ Card: {card.get('title', '')[:50]} - URL: {bool(action_link)}")
            
            # Ensure cards array is never empty
            if not cards:
                cards = [fallback_empty_card()]
            
            logger.info(f"✅ Output: {len(cards)} cards generated")
            print(f"   ✅ Output: {len(cards)} cards generated")
            
            response_data = multiple_product_payload(f"Here are events for {category.title()} in {city.title()}:", cards)
            logger.info(f"Response JSON (first 500 chars): {str(response_data)[:500]}")
            print(f"   📤 Sending response with {len(cards)} cards in Multiple Product format")
            
            print("="*60 + "\n")
            logger.info("="*60)
            
            # Log (non-blocking) - Match Google Sheet columns
            try:
                if SHEET_BEST_URL:
                    log_data = {
                        "Name": "",  # Not available from bot endpoint
                        "Email": "",  # Not available from bot endpoint
                        "Choice": "Book an Event",
                        "Genre": category.title(),
                        "Mood": "",
                        "Suggestion": ", ".join([c.get("title", "")[:50] for c in cards[:3]]),  # First 3 titles
                        "Endpoint": "events_cards",
                        "Category": category.title(),
                        "Preferences": "",
                        "City": city.title() if city else "",
                        "ResultsCount": len(cards),
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    requests.post(SHEET_BEST_URL, json=log_data, timeout=3)
                    logger.info(f"✅ Logged to sheet: {category.title()} in {city} - {len(cards)} results")
            except Exception as e:
                logger.warning(f"⚠️ Logging failed: {e}")
                pass  # Non-blocking
            
            return jsonify(response_data)
            
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"❌ EXCEPTION in events_cards: {str(e)}")
            logger.error(error_msg)
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ events_cards error:", error_msg)
            return jsonify(multiple_product_payload("Unable to fetch events right now.", [fallback_empty_card()])), 400

    @app.route('/recommendations', methods=['POST'])
    def recommendations():
        """
        Endpoint 3: My Pick Combo
        Input: {"mood": "string", "movieGenre": "string", "songType": "string", "diet": "string"}
        Output: {"cards": [...], "movie": {...}, "song": {...}, "food": {...}, "inputs": {...}}
        """
        # Log incoming request (both print and logger for Render visibility)
        logger.info("="*60)
        logger.info("🟡 [REQUEST] POST /recommendations")
        logger.info(f"Time: {datetime.datetime.utcnow().isoformat()}")
        logger.info(f"Remote: {request.remote_addr}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Raw data: {request.get_data(as_text=True)[:200]}")
        
        print("\n" + "="*60)
        print("🟡 [REQUEST] POST /recommendations")
        print(f"   Time: {datetime.datetime.utcnow().isoformat()}")
        print(f"   Remote: {request.remote_addr}")
        print(f"   Content-Type: {request.content_type}")
        
        try:
            # Try to get JSON data - be more flexible with content types
            data = None
            if request.is_json:
                data = request.get_json(force=True)
            elif request.content_type and 'application/json' in request.content_type:
                data = request.get_json(force=True)
            elif request.data:
                try:
                    import json
                    data = json.loads(request.get_data(as_text=True))
                except:
                    pass
            
            # If still no data, try form data
            if not data and request.form:
                data = request.form.to_dict()
            
            logger.info(f"Parsed data: {data}")
            print(f"   📥 Parsed data: {data}")
            
            if not data:
                logger.error("❌ ERROR: No data received or couldn't parse")
                print("   ❌ ERROR: No data received or couldn't parse")
                payload = multiple_product_payload("Please share your mood and preferences to start.", [fallback_empty_card()])
                payload.update({
                    "movie": {"text": "", "url": None, "image": None, "poster": None},
                    "song": {"text": "", "url": None, "image": None, "source": ""},
                    "food": {"text": "", "url": None, "image": None},
                    "inputs": {"mood": "", "movieGenre": "", "songType": "", "diet": ""}
                })
                return jsonify(payload), 400
            
            mood = normalize(safe_get(data, "mood", ""))
            movie_genre = normalize(safe_get(data, "movieGenre", "random"))
            song_type = normalize(safe_get(data, "songType", ""))
            diet = normalize(safe_get(data, "diet", ""))
            
            logger.info(f"Input: mood='{mood}', movieGenre='{movie_genre}', songType='{song_type}', diet='{diet}'")
            print(f"   📥 Input: mood='{mood}', movieGenre='{movie_genre}', songType='{song_type}', diet='{diet}'")
            
            # Get recommendations
            movie = {}
            song = {}
            food = {}
            
            try:
                movie = get_movie_recommendation_with_url(movie_genre, mood) or {}
                song = get_song_recommendation_with_url(song_type, mood) or {}
                food = get_food_recommendation_with_url(diet) or {}
            except Exception as e:
                print(f"⚠️ Error getting recommendations: {e}")
                # Use empty defaults
                movie = {"text": "", "url": None, "image": None, "poster": None}
                song = {"text": "", "url": None, "image": None, "source": ""}
                food = {"text": "", "url": None, "image": None}
            
            # Ensure all fields exist with proper defaults
            movie_result = {
                "text": str(safe_get(movie, "text", "")),
                "url": str(safe_get(movie, "url")) if safe_get(movie, "url") else None,
                "image": str(safe_get(movie, "image")) if safe_get(movie, "image") else None,
                "poster": str(safe_get(movie, "poster")) if safe_get(movie, "poster") else None
            }

            if not movie_result["text"].strip():
                movie_result = fallback_movie_recommendation()
            
            # Determine song source
            song_source = "Spotify"
            if safe_get(song, "url"):
                song_url = str(safe_get(song, "url"))
                if "spotify.com" in song_url:
                    song_source = "Spotify"
                elif "itunes.apple.com" in song_url or "music.apple.com" in song_url:
                    song_source = "iTunes"
            
            song_result = {
                "text": str(safe_get(song, "text", "")),
                "url": str(safe_get(song, "url")) if safe_get(song, "url") else None,
                "image": str(safe_get(song, "image")) if safe_get(song, "image") else None,
                "source": str(safe_get(song, "source", song_source))
            }

            if not song_result["text"].strip():
                song_result = fallback_song_recommendation()
            
            food = {
                "text": str(safe_get(food, "text", "")),
                "url": str(safe_get(food, "url")) if safe_get(food, "url") else None,
                "image": str(safe_get(food, "image")) if safe_get(food, "image") else None
            }

            if not food["text"].strip():
                food = fallback_food_recommendation()
            
            # Create cards from recommendations
            cards = []
            
            # Movie card
            if movie_result.get("text"):
                movie_title = str(movie_result["text"]).replace("🎬", "").strip()
                if " — " in movie_title:
                    movie_title = movie_title.split(" — ")[0].strip()
                cards.append(make_card(
                    title=movie_title[:100] if movie_title else "Movie",
                    desc=f"Movie | {movie_genre.title()}" if movie_genre else "Movie",
                    img=movie_result.get("image") or movie_result.get("poster"),
                    label="View",
                    url=movie_result.get("url")
                ))
            
            # Song card
            if song_result.get("text"):
                song_title = str(song_result["text"]).replace("🎵", "").strip()
                if " — " in song_title:
                    song_title = song_title.split(" — ")[0].strip()
                cards.append(make_card(
                    title=song_title[:100] if song_title else "Song",
                    desc=f"Music | {song_type.title()}" if song_type else "Music",
                    img=song_result.get("image"),
                    label="Listen",
                    url=song_result.get("url")
                ))
            
            # Food card
            if food.get("text"):
                food_title = str(food["text"]).replace("🍕", "").strip()
                if " — " in food_title:
                    food_title = food_title.split(" — ")[0].strip()
                cards.append(make_card(
                    title=food_title[:100] if food_title else "Food",
                    desc=f"Food | {diet.title()}" if diet else "Food",
                    img=food.get("image"),
                    label="View Recipe",
                    url=food.get("url")
                ))
            
            # Ensure cards array is never empty
            if not cards:
                cards = [fallback_empty_card()]
            
            print(f"   ✅ Output: {len(cards)} cards, movie={bool(movie_result.get('text'))}, song={bool(song_result.get('text'))}, food={bool(food.get('text'))}")
            print("="*60 + "\n")
            
            # Log (non-blocking) - Match Google Sheet columns
            try:
                if SHEET_BEST_URL:
                    # Extract suggestions from cards
                    suggestions_list = []
                    if movie_result.get("text"):
                        movie_title = str(movie_result["text"]).replace("🎬", "").split(" — ")[0].strip()[:50]
                        suggestions_list.append(f"Movie: {movie_title}")
                    if song_result.get("text"):
                        song_title = str(song_result["text"]).replace("🎵", "").split(" — ")[0].strip()[:50]
                        suggestions_list.append(f"Song: {song_title}")
                    if food.get("text"):
                        food_title = str(food["text"]).replace("🍕", "").strip()[:50]
                        suggestions_list.append(f"Food: {food_title}")
                    
                    log_data = {
                        "Name": "",  # Not available from bot endpoint
                        "Email": "",  # Not available from bot endpoint
                        "Choice": "My Pick Combo",
                        "Genre": movie_genre.title() if movie_genre else "",
                        "Mood": mood.title() if mood else "",
                        "Suggestion": " | ".join(suggestions_list),
                        "Endpoint": "recommendations",
                        "Category": "Combo",
                        "Preferences": f"Movie: {movie_genre}, Song: {song_type}, Diet: {diet}",
                        "City": "",
                        "ResultsCount": len(cards),
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    requests.post(SHEET_BEST_URL, json=log_data, timeout=3)
                    logger.info(f"✅ Logged to sheet: Combo - {mood} - {len(cards)} results")
            except Exception as e:
                logger.warning(f"⚠️ Logging failed: {e}")
                pass  # Non-blocking
            
            payload = multiple_product_payload("Your personalized combo is ready!", cards)
            payload.update({
                "movie": movie_result,
                "song": song_result,
                "food": food,
                "inputs": {
                    "mood": mood,
                    "movieGenre": movie_genre,
                    "songType": song_type,
                    "diet": diet
                }
            })
            return jsonify(payload)
            
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ Recommendations error:", traceback.format_exc())
            payload = multiple_product_payload("Unable to build a combo right now.", [fallback_empty_card()])
            payload.update({
                "movie": {"text": "", "url": None, "image": None, "poster": None},
                "song": {"text": "", "url": None, "image": None, "source": ""},
                "food": {"text": "", "url": None, "image": None},
                "inputs": {"mood": "", "movieGenre": "", "songType": "", "diet": ""}
            })
            return jsonify(payload), 400
