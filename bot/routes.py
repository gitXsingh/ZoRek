"""
Bot Routes - Zoho SalesIQ Bot Endpoints
All endpoints for Zoho SalesIQ chat bot integration.
"""

from flask import request, jsonify
import datetime
import traceback
import requests
from typing import Dict, List

# Import API functions from app (these will be passed as dependencies)
# This keeps bot module decoupled from app implementation


def create_bot_routes(
    app,
    # API functions
    generate_suggestion,
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
    SEATGEEK_CLIENT_ID: str,
    # Handler functions
    parse_user_message,
    log_to_sheet_func,
    format_salesiq_card,
    format_event_card
):
    """
    Create and register all Zoho SalesIQ bot routes.
    
    Args:
        app: Flask app instance
        ...: All required functions and config
    """
    
    @app.route('/zorek', methods=['POST', 'HEAD'])
    def zorek():
        """
        Main webhook endpoint for Zoho SalesIQ integration.
        Handles Movies, Books, and Food suggestions based on input data.
        Supports both JSON and form-data requests.
        """
        # Zoho sends HEAD first to validate
        if request.method == 'HEAD':
            return '', 200

        try:
            # Universal Input Handling
            if request.is_json:
                data = request.get_json(force=True)
            else:
                data = request.form.to_dict()

            # Normalize input
            choice = str(data.get("choice", "")).strip()
            genre = str(data.get("genre", "random")).strip()
            mood = str(data.get("mood", "")).strip()
            name = str(data.get("name", "")).strip()
            email = str(data.get("email", "")).strip()

            suggestion = generate_suggestion(choice, genre, mood)

            # Log Everything (for analytics/debugging)
            log_data = {
                "name": name,
                "email": email,
                "choice": choice,
                "genre": genre,
                "mood": mood,
                "suggestion": suggestion
            }
            log_to_sheet_func(SHEET_BEST_URL, "/zorek", log_data)

            # Final Response
            return jsonify({"suggestion": suggestion, "status": "success"})

        except Exception as e:
            print("❌ Zorek webhook exception:", traceback.format_exc())
            return jsonify({
                "error": str(e),
                "status": "failed"
            }), 500

    @app.route('/chat', methods=['POST'])
    def chat():
        """
        Rule-based chat endpoint that accepts a message and returns a recommendation.
        Expected JSON: { "message": "...", "name": "...", "email": "..." }
        """
        try:
            data = request.get_json(force=True)
            message = str(data.get("message", "")).strip()
            name = str(data.get("name", "")).strip()
            email = str(data.get("email", "")).strip()

            parsed = parse_user_message(message)
            choice = parsed["choice"]
            genre = parsed["genre"]
            mood = parsed["mood"]

            suggestion = generate_suggestion(choice, genre, mood)
            reply = f"Here's a {choice} recommendation for {genre}:\n{suggestion}"

            # Log to sheet
            log_data = {
                "name": name or "ChatUser",
                "email": email,
                "choice": choice,
                "genre": genre,
                "mood": mood,
                "suggestion": suggestion
            }
            log_to_sheet_func(SHEET_BEST_URL, "/chat", log_data)

            return jsonify({"response": reply, "reply": reply, "choice": choice, "genre": genre})
        except Exception as e:
            print("❌ Chat exception:", traceback.format_exc())
            return jsonify({"error": str(e)}), 400

    @app.route('/suggest_cards', methods=['POST'])
    def suggest_cards():
        """
        Plug 1: Suggest Something - Returns results as SalesIQ cards.
        Standardized format for Zoho SalesIQ plug integration.
        
        Expected JSON:
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
        """
        try:
            data = request.get_json(force=True)
            category = str(data.get("category", "")).strip().lower()
            prefs = data.get("prefs", {}) or {}
            
            # Get items based on category
            items = []
            if category == "movies":
                genre = prefs.get("genre", "")
                min_imdb = float(prefs.get("minImdb", 0) or 0)
                year = str(prefs.get("year", "")).strip()
                items = search_movies_with_filters(genre, min_imdb, year)
            elif category == "books":
                subject = prefs.get("subject", "")
                lang = prefs.get("lang", "")
                items = suggest_books_with_links(subject, lang)
            elif category == "games":
                keyword = prefs.get("keyword", "")
                items = suggest_games_with_links(keyword)
            elif category == "music":
                keyword = prefs.get("songType") or prefs.get("keyword") or prefs.get("query", "")
                items = suggest_music_with_links(keyword)
            elif category == "food":
                diet = prefs.get("diet", "")
                items = [get_food_recommendation_with_url(diet)]
            else:
                return jsonify({"error": "Unknown category. Use: Movies, Books, Games, Food, or Music"}), 400
            
            # Transform to SalesIQ card format
            cards = []
            for it in items[:10]:
                if isinstance(it, dict):
                    card = format_salesiq_card(it, category)
                    cards.append(card)
            
            # Log to Google Sheets
            try:
                if SHEET_BEST_URL:
                    log = {
                        "Endpoint": "suggest_cards",
                        "Category": category,
                        "Preferences": str(prefs),
                        "ResultsCount": len(cards),
                        "Timestamp": str(datetime.datetime.now())
                    }
                    requests.post(SHEET_BEST_URL, json=log, timeout=5)
            except Exception as e:
                print("⚠️ Logging failed:", e)
            
            return jsonify({"cards": cards})
        except Exception as e:
            print("❌ suggest_cards error:", traceback.format_exc())
            return jsonify({"error": str(e)}), 400

    @app.route('/events_cards', methods=['POST'])
    def events_cards():
        """
        Plug 2: Book an Event - Returns events as SalesIQ cards.
        Standardized format for Zoho SalesIQ plug integration.
        
        Expected JSON:
        {
          "category": "Movies|Concerts|Talkshow|Find Events",
          "city": "Mumbai"
        }
        """
        try:
            data = request.get_json(force=True)
            category = str(data.get("category", "")).strip().lower()
            city = str(data.get("city", "")).strip() or "Mumbai"  # Default to Mumbai
            results = []
            
            # Get events based on category
            if category in ["concerts", "talkshow", "theater", "sports"]:
                loc = geocode_city(city) if city else None
                if not loc:
                    # If geocoding fails, still return fallback links
                    results = fallback_event_links(category, city)
                else:
                    lat, lon = loc
                    if SEATGEEK_CLIENT_ID:
                        results = events_from_seatgeek(category, lat, lon)
                        if not results:
                            results = fallback_event_links(category, city)
                    else:
                        results = fallback_event_links(category, city)
            elif category in ["find events", "find"]:
                loc = geocode_city(city) if city else None
                if not loc:
                    results = fallback_event_links("concerts", city)
                else:
                    lat, lon = loc
                    results = events_from_seatgeek("concerts", lat, lon)
                    if not results:
                        results = fallback_event_links("concerts", city)
            elif category == "movies":
                if TMDB_KEY:
                    try:
                        data_resp = requests.get(
                            f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_KEY}&language=en-US&page=1",
                            timeout=10
                        ).json()
                        for m in data_resp.get("results", [])[:10]:
                            title = m.get("title")
                            tmdb_id = m.get("id")
                            poster_path = m.get("poster_path")
                            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                            dt = m.get("release_date", "")
                            # Use BookMyShow for booking
                            bms_url = f"https://in.bookmyshow.com/explore/movies-{city.lower()}"
                            results.append({
                                "text": f"🎟️ {title} — {dt}",
                                "url": bms_url,
                                "poster": poster,
                                "image": poster
                            })
                    except Exception:
                        results = []
                else:
                    try:
                        data_resp = requests.get(
                            "https://itunes.apple.com/search?term=movie&entity=movie&limit=10",
                            timeout=10
                        ).json()
                        for m in data_resp.get("results", []):
                            results.append({
                                "text": f"🎟️ {m.get('trackName','Movie')}",
                                "url": m.get('trackViewUrl')
                            })
                    except Exception:
                        results = []
            else:
                return jsonify({"error": "Unknown event category"}), 400
            
            # Transform to SalesIQ card format
            cards = []
            for it in results[:10]:
                if isinstance(it, dict):
                    card = format_event_card(it, category, city)
                    cards.append(card)
            
            # Log to Google Sheets
            try:
                if SHEET_BEST_URL:
                    log = {
                        "Endpoint": "events_cards",
                        "Category": category,
                        "City": city,
                        "ResultsCount": len(cards),
                        "Timestamp": str(datetime.datetime.now())
                    }
                    requests.post(SHEET_BEST_URL, json=log, timeout=5)
            except Exception as e:
                print("⚠️ Logging failed:", e)
            
            return jsonify({"cards": cards})
        except Exception as e:
            print("❌ events_cards error:", traceback.format_exc())
            return jsonify({"error": str(e)}), 400

    @app.route('/recommendations', methods=['POST'])
    def recommendations():
        """
        Plug 3: My Pick Combo - Returns combined recommendations for movie, song, and food.
        Standardized format for Zoho SalesIQ plug integration.
        
        Expected JSON:
        {
          "mood": "happy",
          "movieGenre": "action",
          "songType": "pop",
          "diet": "veg" | "non-veg"
        }
        """
        try:
            data = request.get_json(force=True) if request.is_json else request.form.to_dict()
            mood = str(data.get("mood", "")).strip()
            movie_genre = str(data.get("movieGenre", "random")).strip()
            song_type = str(data.get("songType", "")).strip()
            diet = str(data.get("diet", "")).strip()

            # Derive suggestions with links
            movie = get_movie_recommendation_with_url(movie_genre, mood)
            song = get_song_recommendation_with_url(song_type, mood)
            food = get_food_recommendation_with_url(diet)

            # Log to sheet
            log_data = {
                "name": "WebChat",
                "email": data.get("email", ""),
                "choice": f"Combined: movie={movie_genre}, song={song_type}, diet={diet}",
                "genre": movie_genre,
                "mood": mood,
                "suggestion": f"{movie.get('text')} | {song.get('text')} | {food.get('text')}"
            }
            log_to_sheet_func(SHEET_BEST_URL, "/recommendations", log_data)

            # Transform to cards format for Zoho SalesIQ compatibility
            cards = []
            
            # Movie card
            if movie and movie.get("text"):
                movie_text = movie.get("text", "")
                movie_title = movie_text.replace("🎬", "").strip()
                if " — " in movie_title:
                    movie_title = movie_title.split(" — ")[0].strip()
                cards.append({
                    "title": movie_title,
                    "imageUrl": movie.get("image") or movie.get("poster"),
                    "description": f"Movie | {movie_genre.title()}" if movie_genre else "Movie",
                    "action": {
                        "label": "View",
                        "url": movie.get("url")
                    }
                })
            
            # Song card
            if song and song.get("text"):
                song_text = song.get("text", "")
                song_title = song_text.replace("🎵", "").strip()
                if " — " in song_title:
                    song_title = song_title.split(" — ")[0].strip()
                cards.append({
                    "title": song_title,
                    "imageUrl": song.get("image"),
                    "description": f"Music | {song_type.title()}" if song_type else "Music",
                    "action": {
                        "label": "Listen",
                        "url": song.get("url")
                    }
                })
            
            # Food card
            if food and food.get("text"):
                food_text = food.get("text", "")
                food_title = food_text.replace("🍕", "").strip()
                if " — " in food_title:
                    food_title = food_title.split(" — ")[0].strip()
                cards.append({
                    "title": food_title,
                    "imageUrl": food.get("image"),
                    "description": f"Food | {diet.title()}" if diet else "Food",
                    "action": {
                        "label": "View Recipe",
                        "url": food.get("url")
                    }
                })
            
            return jsonify({
                "movie": movie,
                "song": song,
                "food": food,
                "cards": cards,  # Zoho SalesIQ compatible format
                "inputs": {
                    "mood": mood,
                    "movieGenre": movie_genre,
                    "songType": song_type,
                    "diet": diet
                }
            })
        except Exception as e:
            print("❌ Recommendations exception:", traceback.format_exc())
            return jsonify({"error": str(e)}), 400


def register_bot_routes(app, **kwargs):
    """Register all bot routes with the Flask app"""
    create_bot_routes(app, **kwargs)

