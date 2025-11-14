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


def make_card(title: str, desc: str = "", img: str = None, label: str = "View", url: str = None) -> dict:
    """Create a standardized card object"""
    return {
        "title": str(title) if title else "No Title",
        "description": str(desc) if desc else "",
        "imageUrl": str(img) if img else None,
        "action": {
            "label": str(label) if label else "Open",
            "url": str(url) if url else None
        }
    }


def fallback_empty_card() -> dict:
    """Return a fallback card when no data is available"""
    return make_card(
        title="No Data",
        desc="Try again later",
        img=None,
        label="Open",
        url=None
    )


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
                return jsonify({"cards": [fallback_empty_card()]}), 400
            
            category = normalize(safe_get(data, "category", ""))
            prefs = safe_get(data, "prefs", {}) or {}
            
            logger.info(f"Input: category='{category}', prefs={prefs}")
            print(f"   📥 Input: category='{category}', prefs={prefs}")
            
            if not category:
                logger.error("❌ ERROR: No category provided")
                print("   ❌ ERROR: No category provided")
                return jsonify({"cards": [fallback_empty_card()]}), 400
            
            # Get items based on category
            items = []
            try:
                if category == "movies":
                    genre = normalize(safe_get(prefs, "genre", ""))
                    min_imdb = float(safe_get(prefs, "minImdb", 0) or 0)
                    year = normalize(safe_get(prefs, "year", ""))
                    items = search_movies_with_filters(genre, min_imdb, year)
                elif category == "books":
                    subject = normalize(safe_get(prefs, "subject", ""))
                    lang = normalize(safe_get(prefs, "lang", ""))
                    items = suggest_books_with_links(subject, lang)
                elif category == "games":
                    keyword = normalize(safe_get(prefs, "keyword", ""))
                    items = suggest_games_with_links(keyword)
                elif category == "music":
                    keyword = normalize(safe_get(prefs, "songType") or safe_get(prefs, "keyword") or safe_get(prefs, "query", ""))
                    items = suggest_music_with_links(keyword)
                elif category == "food":
                    diet = normalize(safe_get(prefs, "diet", ""))
                    food_item = get_food_recommendation_with_url(diet)
                    items = [food_item] if food_item else []
                else:
                    items = []
            except Exception as e:
                print(f"⚠️ Error fetching items for {category}: {e}")
                items = []
            
            # Transform to cards format
            cards = []
            for it in (items or [])[:10]:
                if isinstance(it, dict):
                    text = safe_get(it, "text", "")
                    url = safe_get(it, "url")
                    image = safe_get(it, "image") or safe_get(it, "poster")
                    
                    # Clean title from text
                    title = text.replace("🎬", "").replace("📚", "").replace("🎮", "").replace("🎵", "").replace("🍕", "").strip()
                    if " — " in title:
                        title = title.split(" — ")[0].strip()
                    if "—" in title:
                        title = title.split("—")[0].strip()
                    
                    # Extract description
                    desc = category.title()
                    if "⭐" in text:
                        desc = text.split("⭐")[1].strip() if "⭐" in text else desc
                    
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
                    
                    cards.append(make_card(
                        title=title[:100] if title else "Unknown",
                        desc=desc[:200] if desc else category.title(),
                        img=str(image) if image else None,
                        label=action_label,
                        url=str(url) if url else None
                    ))
            
            # Ensure cards array is never empty
            if not cards:
                cards = [fallback_empty_card()]
            
            logger.info(f"✅ Output: {len(cards)} cards generated")
            print(f"   ✅ Output: {len(cards)} cards generated")
            print("="*60 + "\n")
            logger.info("="*60)
            
            # Log (non-blocking)
            try:
                if SHEET_BEST_URL:
                    requests.post(SHEET_BEST_URL, json={
                        "Endpoint": "suggest_cards",
                        "Category": category,
                        "ResultsCount": len(cards),
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }, timeout=3)
            except Exception:
                pass  # Non-blocking
            
            return jsonify({"cards": cards})
            
        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(f"❌ EXCEPTION in suggest_cards: {str(e)}")
            logger.error(error_msg)
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ suggest_cards error:", error_msg)
            return jsonify({"cards": [fallback_empty_card()]}), 400

    @app.route('/events_cards', methods=['POST'])
    def events_cards():
        """
        Endpoint 2: Book an Event
        Input: {"category": "string", "city": "string"}
        Output: {"cards": [{title, description, imageUrl, action: {label, url}}]}
        """
        # Log incoming request
        print("\n" + "="*60)
        print("🟢 [REQUEST] POST /events_cards")
        print(f"   Time: {datetime.datetime.utcnow().isoformat()}")
        print(f"   Headers: {dict(request.headers)}")
        print(f"   Remote: {request.remote_addr}")
        
        try:
            # Validate and parse input
            if not request.is_json:
                print("   ❌ ERROR: Not JSON")
                return jsonify({"cards": [fallback_empty_card()]}), 400
            
            data = request.get_json(force=True)
            category = normalize(safe_get(data, "category", ""))
            city = normalize(safe_get(data, "city", "")) or "mumbai"  # Default fallback
            
            print(f"   📥 Input: category='{category}', city='{city}'")
            
            if not category:
                print("   ❌ ERROR: No category provided")
                return jsonify({"cards": [fallback_empty_card()]}), 400
            
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
            for it in (results or [])[:10]:
                if isinstance(it, dict):
                    text = safe_get(it, "text", "")
                    url = safe_get(it, "url")
                    image = safe_get(it, "image") or safe_get(it, "poster")
                    
                    title = text.replace("🎟️", "").strip()
                    if "—" in title:
                        title = title.split("—")[0].strip()
                    
                    desc = f"Event in {city.title()}"
                    if category == "movies":
                        desc = f"Now Playing in {city.title()}"
                    elif category == "concerts":
                        desc = f"Concert in {city.title()}"
                    
                    cards.append(make_card(
                        title=title[:100] if title else "Event",
                        desc=desc,
                        img=str(image) if image else None,
                        label="Book Tickets",
                        url=str(url) if url else None
                    ))
            
            # Ensure cards array is never empty
            if not cards:
                cards = [fallback_empty_card()]
            
            print(f"   ✅ Output: {len(cards)} cards generated")
            print("="*60 + "\n")
            
            # Log (non-blocking)
            try:
                if SHEET_BEST_URL:
                    requests.post(SHEET_BEST_URL, json={
                        "Endpoint": "events_cards",
                        "Category": category,
                        "City": city,
                        "ResultsCount": len(cards),
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }, timeout=3)
            except Exception:
                pass  # Non-blocking
            
            return jsonify({"cards": cards})
            
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ events_cards error:", traceback.format_exc())
            return jsonify({"cards": [fallback_empty_card()]}), 400

    @app.route('/recommendations', methods=['POST'])
    def recommendations():
        """
        Endpoint 3: My Pick Combo
        Input: {"mood": "string", "movieGenre": "string", "songType": "string", "diet": "string"}
        Output: {"cards": [...], "movie": {...}, "song": {...}, "food": {...}, "inputs": {...}}
        """
        # Log incoming request
        print("\n" + "="*60)
        print("🟡 [REQUEST] POST /recommendations")
        print(f"   Time: {datetime.datetime.utcnow().isoformat()}")
        print(f"   Headers: {dict(request.headers)}")
        print(f"   Remote: {request.remote_addr}")
        
        try:
            # Validate and parse input
            if not request.is_json:
                print("   ❌ ERROR: Not JSON")
                return jsonify({
                    "cards": [fallback_empty_card()],
                    "movie": {"text": "", "url": None, "image": None, "poster": None},
                    "song": {"text": "", "url": None, "image": None, "source": ""},
                    "food": {"text": "", "url": None, "image": None},
                    "inputs": {"mood": "", "movieGenre": "", "songType": "", "diet": ""}
                }), 400
            
            data = request.get_json(force=True)
            mood = normalize(safe_get(data, "mood", ""))
            movie_genre = normalize(safe_get(data, "movieGenre", "random"))
            song_type = normalize(safe_get(data, "songType", ""))
            diet = normalize(safe_get(data, "diet", ""))
            
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
            
            food = {
                "text": str(safe_get(food, "text", "")),
                "url": str(safe_get(food, "url")) if safe_get(food, "url") else None,
                "image": str(safe_get(food, "image")) if safe_get(food, "image") else None
            }
            
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
            
            # Log (non-blocking)
            try:
                if SHEET_BEST_URL:
                    requests.post(SHEET_BEST_URL, json={
                        "Endpoint": "recommendations",
                        "Mood": mood,
                        "MovieGenre": movie_genre,
                        "SongType": song_type,
                        "Diet": diet,
                        "Timestamp": datetime.datetime.utcnow().isoformat()
                    }, timeout=3)
            except Exception:
                pass  # Non-blocking
            
            return jsonify({
                "cards": cards,
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
            
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            print("="*60 + "\n")
            print("❌ Recommendations error:", traceback.format_exc())
            return jsonify({
                "cards": [fallback_empty_card()],
                "movie": {"text": "", "url": None, "image": None, "poster": None},
                "song": {"text": "", "url": None, "image": None, "source": ""},
                "food": {"text": "", "url": None, "image": None},
                "inputs": {"mood": "", "movieGenre": "", "songType": "", "diet": ""}
            }), 400
