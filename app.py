from flask import Flask, request, jsonify, render_template
import requests
import datetime
import random
import traceback

app = Flask(__name__)

# ====== CONFIG ======
OMDB_KEY = "24b393c0"
SPOONACULAR_KEY = "7a3b4893233c41d3b327eacdba876813"
SHEET_BEST_URL = "https://api.sheetbest.com/sheets/766d80b7-7fbe-4480-b3d1-6b44795a9cef"
SEATGEEK_CLIENT_ID = ""  # optional: add your SeatGeek client id for events
TMDB_KEY = "d0db65f7a9ba6865e6216b9ade630204"  # TMDB API key for now-playing movies
SPOTIFY_CLIENT_ID = ""  # optional: set for OAuth
SPOTIFY_CLIENT_SECRET = ""  # optional: set for OAuth
SPOTIFY_CLIENT_ID = "c21728adef8843be87cb53a0f33f7204"
SPOTIFY_CLIENT_SECRET = "1920660f4f88408ab148f79892281213"
SPOTIFY_REDIRECT_URI = "https://zorek.onrender.com/oauth/spotify/callback"  # must match Spotify app settings
OPENAI_API_KEY = ""   # optional: add for AI commentary
# ====================

SPOTIFY_TOKEN = {"access_token": None, "expires_at": 0}

def _now_ts() -> int:
    return int(datetime.datetime.utcnow().timestamp())

def set_spotify_token(access_token: str, expires_in: int):
    SPOTIFY_TOKEN["access_token"] = access_token
    SPOTIFY_TOKEN["expires_at"] = _now_ts() + int(expires_in or 0) - 30

def spotify_token_valid() -> bool:
    return bool(SPOTIFY_TOKEN.get("access_token")) and _now_ts() < SPOTIFY_TOKEN.get("expires_at", 0)

def normalize_genre_search_term(raw: str) -> str:
    """
    Normalize user-provided genres into better search terms for OMDb.
    This does not strictly filter by OMDb genre (not supported), but improves relevance.
    """
    term = (raw or "").strip().lower()
    synonyms = {
        "science fiction": "sci-fi",
        "scifi": "sci-fi",
        "sci fi": "sci-fi",
        "romcom": "romance",
        "super hero": "superhero",
        "super-hero": "superhero",
        "bio": "biography",
        "docu": "documentary",
        "toon": "animation",
        "kids": "family",
        "ww2": "war",
    }
    if term in synonyms:
        return synonyms[term]
    return term

def canon_genre_tokens(user_genre: str) -> list[str]:
    """
    Map user genre into canonical OMDb genre tokens used in 'Genre' field.
    We allow multiple possible tokens for broader intents (e.g., 'superhero').
    """
    g = (user_genre or "").strip().lower()
    mapping = {
        "action": ["Action"],
        "adventure": ["Adventure"],
        "animation": ["Animation"],
        "biography": ["Biography"],
        "comedy": ["Comedy"],
        "crime": ["Crime"],
        "documentary": ["Documentary"],
        "drama": ["Drama"],
        "family": ["Family"],
        "fantasy": ["Fantasy"],
        "history": ["History"],
        "horror": ["Horror"],
        "music": ["Music"],
        "musical": ["Musical"],
        "mystery": ["Mystery"],
        "romance": ["Romance"],
        "sci-fi": ["Sci-Fi"],
        "science fiction": ["Sci-Fi"],
        "sport": ["Sport"],
        "thriller": ["Thriller"],
        "war": ["War"],
        "western": ["Western"],
        "film-noir": ["Film-Noir"],
        "noir": ["Film-Noir", "Thriller", "Crime"],
        "superhero": ["Action", "Adventure", "Sci-Fi", "Fantasy"],
        "survival": ["Adventure", "Thriller", "Drama"],
        "romcom": ["Romance", "Comedy"],
    }
    # Normalize through previous helper for sci-fi etc.
    base = normalize_genre_search_term(g)
    return mapping.get(base, [base.title()])  # default to Title Case token

def tmdb_genre_ids(user_genre: str) -> list[int]:
    """
    Map user genres to TMDB numeric genre IDs for strict discovery.
    https://developer.themoviedb.org/reference/genre-movie-list
    """
    base = normalize_genre_search_term((user_genre or "").strip().lower())
    tmdb_map = {
        "action": [28],
        "adventure": [12],
        "animation": [16],
        "biography": [36, 99],  # history / documentary
        "comedy": [35],
        "crime": [80],
        "documentary": [99],
        "drama": [18],
        "family": [10751],
        "fantasy": [14],
        "history": [36],
        "horror": [27],
        "music": [10402],
        "musical": [10402],
        "mystery": [9648],
        "romance": [10749],
        "sci-fi": [878],
        "science fiction": [878],
        "sport": [10770],  # no sport; TV Movie closest; leave empty otherwise
        "thriller": [53],
        "war": [10752],
        "western": [37],
        "noir": [80, 53],
        "superhero": [28, 12, 878],
        "survival": [12, 53, 18],
        "romcom": [10749, 35],
    }
    return tmdb_map.get(base, [])

def discover_movies_via_tmdb(genre: str, min_imdb: float = 0.0, year: str = "") -> list[dict]:
    """
    Use TMDB Discover API with strict genre IDs; enrich with IMDb rating via OMDb.
    Returns list of {text, url, poster, imdbRating, year}
    """
    if not TMDB_KEY:
        return []
    ids = tmdb_genre_ids(genre)
    if not ids:
        return []
    try:
        params = {
            "api_key": TMDB_KEY,
            "with_genres": ",".join(str(i) for i in ids),
            "language": "en-US",
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "page": 1
        }
        if year:
            params["primary_release_year"] = str(year)
        d = requests.get("https://api.themoviedb.org/3/discover/movie", params=params, timeout=10).json()
        results = []
        for m in (d.get("results") or [])[:10]:
            tmdb_id = m.get("id")
            title = m.get("title") or m.get("name")
            release_date = (m.get("release_date") or "")[:4]
            poster_path = m.get("poster_path")
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            imdb_id = None
            try:
                ext = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids", params={"api_key": TMDB_KEY}, timeout=8).json()
                imdb_id = ext.get("imdb_id")
            except Exception:
                imdb_id = None
            imdb_rating_val = "N/A"
            if imdb_id:
                detail = requests.get(f"https://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}&plot=short", timeout=8).json()
                r = detail.get("imdbRating")
                if r and r != "N/A":
                    imdb_rating_val = r
            # Apply rating filter if provided
            try:
                if min_imdb and imdb_rating_val != "N/A" and float(imdb_rating_val) < float(min_imdb):
                    continue
            except Exception:
                pass
            url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else f"https://www.themoviedb.org/movie/{tmdb_id}"
            results.append({
                "text": f"🎬 {title} ({release_date or 'N/A'}) — ⭐ {imdb_rating_val}",
                "url": url,
                "poster": poster,
                "imdbRating": imdb_rating_val,
                "year": release_date or "N/A"
            })
        return results or [{"text": "No movies matched your filters.", "url": None}]
    except Exception as exc:
        return [{"text": f"⚠️ TMDB discover error: {str(exc)}", "url": None}]

def generate_suggestion(choice: str, genre: str, mood: str = "") -> str:
    """
    Generate a recommendation based on choice and genre.
    Supported choices: Movies, Books, Food
    """
    normalized_choice = (choice or "").lower()
    normalized_genre = (genre or "random").lower()

    if "movie" in normalized_choice:
        try:
            # Use filtered search to ensure genre match
            items = search_movies_with_filters(normalized_genre, 0.0, "")
            for it in items:
                if isinstance(it, dict) and it.get("text"):
                    return it["text"]
            return "🎬 Couldn't find a movie for that genre. Try another one?"
        except Exception as exc:
            return f"⚠️ Movie API error: {str(exc)}"

    if "book" in normalized_choice:
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{normalized_genre}"
            res = requests.get(url, timeout=8).json()
            if "items" in res and res["items"]:
                result = random.choice(res["items"])
                title = result.get("volumeInfo", {}).get("title", "Unknown Title")
                return f"📚 {title}"
            return "📚 Couldn't find a book for that genre. Try another one?"
        except Exception as exc:
            return f"⚠️ Book API error: {str(exc)}"

    if "food" in normalized_choice or "recipe" in normalized_choice:
        try:
            url = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
            res = requests.get(url, timeout=8).json()
            if "recipes" in res and res["recipes"]:
                recipe = res["recipes"][0]
                return f"🍕 {recipe.get('title', 'Unknown Recipe')}"
            return "🍕 Couldn't fetch a recipe right now. Try again?"
        except Exception as exc:
            return f"⚠️ Food API error: {str(exc)}"

    return "Please choose from Movies, Books, or Food."


def parse_user_message(message: str) -> dict:
    """
    Very simple rule-based parser to infer choice and genre from a freeform message.
    Returns a dict with keys: choice, genre, mood
    """
    text = (message or "").strip()
    lower = text.lower()

    # Infer choice
    if any(k in lower for k in ["movie", "film", "cinema"]):
        choice = "Movies"
    elif any(k in lower for k in ["book", "novel", "read"]):
        choice = "Books"
    elif any(k in lower for k in ["food", "recipe", "cook", "eat", "meal"]):
        choice = "Food"
    else:
        choice = "Movies"

    # Try to infer genre from common keywords or "genre:" or "for/in" phrases
    common_genres = [
        # Core
        "action", "adventure", "animation", "biography", "comedy", "crime",
        "documentary", "drama", "family", "fantasy", "history", "horror",
        "music", "musical", "mystery", "romance", "sci-fi", "science fiction",
        "sport", "thriller", "war", "western",
        # Extras
        "superhero", "survival", "noir"
    ]
    genre = "random"

    # explicit marker: genre: X
    if "genre:" in lower:
        after = lower.split("genre:", 1)[1].strip()
        genre = after.split()[0].strip(",.!?") or "random"
    else:
        # keyword scan
        for g in common_genres:
            if g in lower:
                genre = "sci-fi" if g == "science fiction" else g
                break
        # simple "for X" or "in X"
        if genre == "random":
            for token in [" for ", " in "]:
                if token in lower:
                    candidate = lower.split(token, 1)[1].split()[0].strip(",.!?")
                    if candidate and candidate.isalpha():
                        genre = candidate
                    break

    return {"choice": choice, "genre": genre, "mood": ""}

def generate_music_suggestion(song_type: str = "", mood: str = "") -> str:
    """
    Suggest a song using iTunes Search API based on song type or mood.
    """
    term_source = (song_type or mood or "popular").strip()
    term = term_source.replace(" ", "+")
    try:
        url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=25"
        res = requests.get(url, timeout=8)
        data = res.json()
        results = data.get("results", [])
        if results:
            import random as _random
            track = _random.choice(results)
            track_name = track.get("trackName", "Unknown Track")
            artist = track.get("artistName", "Unknown Artist")
            return f"🎵 {track_name} — {artist}"
        return "🎵 Couldn't find a song right now. Try another type?"
    except Exception as exc:
        return f"⚠️ Music API error: {str(exc)}"

def generate_food_suggestion_by_diet(diet: str = "") -> str:
    """
    Suggest a recipe using Spoonacular, optionally filtered by vegetarian diet.
    """
    try:
        base = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
        diet = (diet or "").strip().lower()
        if diet in ["veg", "vegetarian", "vegan"]:
            url = base + "&tags=vegetarian"
        else:
            url = base
        res = requests.get(url, timeout=8).json()
        if "recipes" in res and res["recipes"]:
            recipe = res["recipes"][0]
            return f"🍕 {recipe.get('title', 'Unknown Recipe')}"
        return "🍕 Couldn't fetch a recipe right now. Try again?"
    except Exception as exc:
        return f"⚠️ Food API error: {str(exc)}"

def get_movie_recommendation_with_url(genre: str, mood: str = "") -> dict:
    """
    Return a dict with text and url for a movie suggestion.
    """
    try:
        # Prefer items that truly match genre tokens
        results = search_movies_with_filters(genre, 0.0, "")
        for it in results:
            if it.get("url"):
                return {"text": it.get("text"), "url": it.get("url")}
        # fallback
        q = normalize_genre_search_term((genre or "random"))
        url = f"https://www.omdbapi.com/?apikey={OMDB_KEY}&type=movie&s={q}"
        res = requests.get(url, timeout=8).json()
        if res.get("Search"):
            first = res["Search"][0]
            imdb_id = first.get("imdbID")
            d = requests.get(f"https://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}&plot=short", timeout=8).json()
            title = d.get("Title", first.get("Title", "Unknown"))
            year = d.get("Year", first.get("Year", "N/A"))
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None
            return {"text": f"🎬 {title} ({year})", "url": imdb_url}
        return {"text": "🎬 Couldn't find a movie for that genre. Try another one?", "url": None}
    except Exception as exc:
        return {"text": f"⚠️ Movie API error: {str(exc)}", "url": None}

def get_song_recommendation_with_url(song_type: str = "", mood: str = "") -> dict:
    """
    Return a dict with text, url, and image for a song suggestion.
    Prefer Spotify if OAuth token available, else fallback to iTunes.
    """
    query = (song_type or mood or "popular").strip()
    # Try Spotify
    if spotify_token_valid():
        try:
            headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN['access_token']}"}
            params = {"q": query, "type": "track", "limit": 25}
            resp = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=8)
            data = resp.json()
            items = (data.get("tracks", {}) or {}).get("items", [])
            if items:
                track = random.choice(items)
                name = track.get("name", "Unknown Track")
                artists = ", ".join([a.get("name") for a in track.get("artists", [])]) or "Unknown Artist"
                url = (track.get("external_urls") or {}).get("spotify")
                images = ((track.get("album") or {}).get("images") or [])
                image = images[0]["url"] if images else None
                return {"text": f"🎵 {name} — {artists}", "url": url, "image": image}
        except Exception as exc:
            pass
    # Fallback to iTunes
    try:
        term = query.replace(" ", "+")
        url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=25"
        res = requests.get(url, timeout=8)
        data = res.json()
        results = data.get("results", [])
        if results:
            track = random.choice(results)
            track_name = track.get("trackName", "Unknown Track")
            artist = track.get("artistName", "Unknown Artist")
            link = track.get("trackViewUrl") or track.get("collectionViewUrl") or track.get("artistViewUrl")
            img = track.get("artworkUrl100") or track.get("artworkUrl60")
            return {"text": f"🎵 {track_name} — {artist}", "url": link, "image": img}
        return {"text": "🎵 Couldn't find a song right now. Try another type?", "url": None}
    except Exception as exc:
        return {"text": f"⚠️ Music API error: {str(exc)}", "url": None}

def get_food_recommendation_with_url(diet: str = "") -> dict:
    """
    Return a dict with text and url for a food suggestion from Spoonacular.
    """
    try:
        base = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
        d = (diet or "").strip().lower()
        url = base + "&tags=vegetarian" if d in ["veg", "vegetarian", "vegan"] else base
        res = requests.get(url, timeout=8).json()
        if "recipes" in res and res["recipes"]:
            recipe = res["recipes"][0]
            title = recipe.get("title", "Unknown Recipe")
            link = recipe.get("sourceUrl") or recipe.get("spoonacularSourceUrl")
            img = recipe.get("image")
            return {"text": f"🍕 {title}", "url": link, "image": img}
        return {"text": "🍕 Couldn't fetch a recipe right now. Try again?", "url": None}
    except Exception as exc:
        return {"text": f"⚠️ Food API error: {str(exc)}", "url": None}

def search_movies_with_filters(genre: str = "", min_imdb: float = 0.0, year: str = "") -> list[dict]:
    """
    Use OMDb to search movies by keyword (genre text), optionally filter by year and imdb rating.
    Returns list of {text, url, poster, imdbRating, year}
    """
    # Prefer strict TMDB discover when genre provided and TMDB is configured
    if TMDB_KEY and genre:
        tmdb_results = discover_movies_via_tmdb(genre, min_imdb, year)
        # If TMDB returned meaningful items (not solely an error), use them
        if tmdb_results and not (len(tmdb_results) == 1 and "error" in (tmdb_results[0].get("text","").lower())):
            return tmdb_results

    q = normalize_genre_search_term(genre or "popular")
    url = f"https://www.omdbapi.com/?apikey={OMDB_KEY}&type=movie&s={q}"
    try:
        res = requests.get(url, timeout=10).json()
        items = res.get("Search", [])[:10]
        results = []
        for it in items:
            imdb_id = it.get("imdbID")
            if not imdb_id:
                continue
            # fetch details
            d = requests.get(f"https://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}&plot=short", timeout=10).json()
            # Genre match: ensure one of the canonical tokens appears in detail Genre
            desired_tokens = [t.lower() for t in canon_genre_tokens(genre)]
            detail_genre = (d.get("Genre") or "").lower()
            if genre and desired_tokens:
                if not any(tok.lower() in detail_genre for tok in desired_tokens):
                    continue
            imdb_rating = 0.0
            try:
                imdb_rating = float(d.get("imdbRating")) if d.get("imdbRating") not in [None, "N/A"] else 0.0
            except Exception:
                imdb_rating = 0.0
            year_ok = True
            if year and str(d.get("Year", "")).startswith(str(year)):
                year_ok = True
            elif year:
                year_ok = False
            if imdb_rating >= float(min_imdb or 0) and year_ok:
                results.append({
                    "text": f"🎬 {d.get('Title','Unknown')} ({d.get('Year','N/A')}) — ⭐ {d.get('imdbRating','N/A')}",
                    "url": f"https://www.imdb.com/title/{imdb_id}/",
                    "poster": d.get("Poster") if d.get("Poster") and d.get("Poster") != "N/A" else None,
                    "imdbRating": d.get("imdbRating","N/A"),
                    "year": d.get("Year","N/A")
                })
        return results or [{"text": "No movies matched your filters.", "url": None}]
    except Exception as exc:
        return [{"text": f"⚠️ Movie search error: {str(exc)}", "url": None}]

def suggest_books_with_links(subject: str = "", lang: str = "") -> list[dict]:
    q = subject or "bestsellers"
    url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{q}"
    if lang:
        url += f"&langRestrict={lang}"
    try:
        data = requests.get(url, timeout=10).json()
        items = data.get("items", [])[:10]
        results = []
        for it in items:
            info = it.get("volumeInfo", {})
            title = info.get("title", "Unknown Title")
            link = info.get("infoLink") or info.get("previewLink")
            authors = ", ".join(info.get("authors", [])[:2]) if info.get("authors") else ""
            image = (info.get("imageLinks") or {}).get("thumbnail")
            results.append({
                "text": f"📚 {title}" + (f" — {authors}" if authors else ""),
                "url": link,
                "image": image
            })
        return results or [{"text": "No books found.", "url": None}]
    except Exception as exc:
        return [{"text": f"⚠️ Book search error: {str(exc)}", "url": None}]

def suggest_games_with_links(keyword: str = "") -> list[dict]:
    """
    Use CheapShark API to find games by title keyword.
    """
    term = (keyword or "the").strip()
    try:
        data = requests.get(f"https://www.cheapshark.com/api/1.0/games?title={term}&limit=10", timeout=10).json()
        results = []
        for g in data:
            title = g.get("external")
            steam_appid = g.get("steamAppID")
            game_id = g.get("gameID")
            url = f"https://store.steampowered.com/app/{steam_appid}/" if steam_appid else f"https://www.cheapshark.com/price?gameID={game_id}"
            thumb = g.get("thumb")
            results.append({"text": f"🎮 {title}", "url": url, "image": thumb})
        return results or [{"text": "No games found.", "url": None}]
    except Exception as exc:
        return [{"text": f"⚠️ Game search error: {str(exc)}", "url": None}]

def geocode_city(city: str) -> tuple[float, float] | None:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": city, "format": "json", "limit": 1}, headers={"User-Agent": "ZoRekBot/1.0"}, timeout=10)
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except Exception:
        return None

def events_from_seatgeek(category: str, lat: float, lon: float) -> list[dict]:
    """
    Fetch events from SeatGeek by category and location.
    Categories mapped: concerts -> concert, talkshow -> comedy, theater, etc.
    """
    if not SEATGEEK_CLIENT_ID:
        # Caller should handle graceful fallback when SeatGeek is not configured
        return []
    type_map = {
        "concerts": "concert",
        "talkshow": "comedy",
        "theater": "theater",
        "sports": "sports"
    }
    t = type_map.get(category.lower(), "concert")
    try:
        url = "https://api.seatgeek.com/2/events"
        params = {
            "client_id": SEATGEEK_CLIENT_ID,
            "type": t,
            "lat": lat,
            "lon": lon,
            "range": "30mi",
            "per_page": 10
        }
        data = requests.get(url, params=params, timeout=12).json()
        evs = []
        for e in data.get("events", []):
            title = e.get("title")
            dt = e.get("datetime_local", "")[:16].replace("T", " ")
            venue = (e.get("venue", {}) or {}).get("name")
            url = e.get("url")
            evs.append({"text": f"📅 {title} — {dt} @ {venue}", "url": url})
        return evs or [{"text": "No events found nearby.", "url": None}]
    except Exception as exc:
        return [{"text": f"⚠️ SeatGeek error: {str(exc)}", "url": None}]

def fallback_event_links(category: str, city: str) -> list[dict]:
    """
    Provide helpful fallback links if SeatGeek is not configured.
    Uses Google search and BookMyShow (popular in India) URLs.
    """
    city_q = (city or "your city").strip()
    cat = (category or "events").strip()
    google_q = requests.utils.quote(f"{cat} near {city_q}")
    google_url = f"https://www.google.com/search?q={google_q}"
    # BookMyShow city slug (basic sanitization)
    slug = city_q.replace(" ", "-").lower()
    # Broad events page; specific categories vary by region on BMS
    bms_url = f"https://in.bookmyshow.com/explore/events-{slug}"
    return [
        {"text": f"🔎 Search {cat} near {city_q}", "url": google_url},
        {"text": f"🎟️ BookMyShow {cat} in {city_q}", "url": bms_url},
    ]


@app.route('/')
def home():
    return render_template("index.html")


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
        # ====== Universal Input Handling ======
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

        # ====== Log Everything (for analytics/debugging) ======
        log = {
            "Name": name,
            "Email": email,
            "Choice": choice,
            "Genre": genre,
            "Mood": mood,
            "Suggestion": suggestion,
            "Timestamp": str(datetime.datetime.now())
        }

        try:
            requests.post(SHEET_BEST_URL, json=log, timeout=5)
        except Exception as e:
            print("⚠️ Logging failed:", e)

        # ====== Final Response ======
        return jsonify({"suggestion": suggestion, "status": "success"})

    except Exception as e:
        print("❌ Exception:", traceback.format_exc())
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc(),
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
        log = {
            "Name": name or "ChatUser",
            "Email": email,
            "Choice": choice,
            "Genre": genre,
            "Mood": mood,
            "Suggestion": suggestion,
            "Timestamp": str(datetime.datetime.now())
        }
        try:
            requests.post(SHEET_BEST_URL, json=log, timeout=5)
        except Exception as e:
            print("⚠️ Logging failed:", e)

        return jsonify({"reply": reply, "choice": choice, "genre": genre})
    except Exception as e:
        print("❌ Chat exception:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/recommendations', methods=['POST'])
def recommendations():
    """
    Accepts a combined preferences payload and returns recommendations for
    movie, song, and food.
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

        # Optional: log to sheet as a single combined record
        log = {
            "Name": "WebChat",
            "Email": "",
            "Choice": f"Combined: movie={movie_genre}, song={song_type}, diet={diet}",
            "Genre": movie_genre,
            "Mood": mood,
            "Suggestion": f"{movie.get('text')} | {song.get('text')} | {food.get('text')}",
            "Timestamp": str(datetime.datetime.now())
        }
        try:
            requests.post(SHEET_BEST_URL, json=log, timeout=5)
        except Exception as e:
            print("⚠️ Logging failed:", e)

        return jsonify({
            "movie": movie,
            "song": song,
            "food": food,
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

@app.route('/suggest', methods=['POST'])
def suggest():
    """
    Suggest something endpoint.
    Expects JSON:
    {
      "category": "Movies|Books|Games|Food",
      "prefs": { ... }  // category-specific
    }
    """
    try:
        data = request.get_json(force=True)
        category = str(data.get("category", "")).strip().lower()
        prefs = data.get("prefs", {}) or {}
        results = []

        if category == "movies":
            genre = prefs.get("genre", "")
            min_imdb = float(prefs.get("minImdb", 0) or 0)
            year = str(prefs.get("year", "")).strip()
            results = search_movies_with_filters(genre, min_imdb, year)
        elif category == "books":
            subject = prefs.get("subject", "")
            lang = prefs.get("lang", "")
            results = suggest_books_with_links(subject, lang)
        elif category == "games":
            keyword = prefs.get("keyword", "")
            results = suggest_games_with_links(keyword)
        elif category == "food":
            diet = prefs.get("diet", "")
            results = [get_food_recommendation_with_url(diet)]
        else:
            return jsonify({"error": "Unknown category"}), 400

        return jsonify({"items": results})
    except Exception as e:
        print("❌ Suggest exception:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/events', methods=['POST'])
def events():
    """
    Book an event flow.
    Expects JSON:
    {
      "category": "Movies|Talkshow|Concerts|Find events",
      "city": "City name" // used for location-based search
    }
    """
    try:
        data = request.get_json(force=True)
        category = str(data.get("category", "")).strip().lower()
        city = str(data.get("city", "")).strip()
        results = []

        if category in ["concerts", "talkshow", "theater", "sports"]:
            loc = geocode_city(city) if city else None
            if not loc:
                return jsonify({"error": "Could not determine location"}), 400
            lat, lon = loc
            # Try SeatGeek; if not configured, show helpful links instead
            if SEATGEEK_CLIENT_ID:
                results = events_from_seatgeek(category, lat, lon)
                if not results:
                    results = fallback_event_links(category, city)
            else:
                results = fallback_event_links(category, city)
        elif category in ["find events", "find"]:
            loc = geocode_city(city) if city else None
            if not loc:
                return jsonify({"error": "Could not determine location"}), 400
            lat, lon = loc
            # default to concert mix
            results = events_from_seatgeek("concerts", lat, lon)
        elif category == "movies":
            # If TMDB key configured, fetch now-playing; else fallback to popular iTunes movies
            if TMDB_KEY:
                try:
                    data = requests.get(f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_KEY}&language=en-US&page=1", timeout=10).json()
                    items = []
                    for m in data.get("results", [])[:10]:
                        title = m.get("title")
                        url = f"https://www.themoviedb.org/movie/{m.get('id')}"
                        dt = m.get("release_date", "")
                        items.append({"text": f"🎟️ {title} — {dt}", "url": url})
                    results = items or [{"text": "No now-playing movies found.", "url": None}]
                except Exception as exc:
                    results = [{"text": f"TMDB error: {str(exc)}", "url": None}]
            else:
                try:
                    data = requests.get("https://itunes.apple.com/search?term=movie&entity=movie&limit=10", timeout=10).json()
                    items = [{"text": f"🎟️ {m.get('trackName','Movie')}", "url": m.get('trackViewUrl')} for m in data.get("results", [])]
                    results = items or [{"text": "No movies found.", "url": None}]
                except Exception as exc:
                    results = [{"text": f"iTunes error: {str(exc)}", "url": None}]
        else:
            return jsonify({"error": "Unknown event category"}), 400

        return jsonify({"items": results})
    except Exception as e:
        print("❌ Events exception:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/suggest_cards', methods=['POST'])
def suggest_cards():
    """
    Returns results as cards: [{title, imageUrl, description, action:{label,url}}]
    Mirrors /suggest but transforms items for easy SalesIQ display.
    """
    try:
        data = request.get_json(force=True)
        category = str(data.get("category", "")).strip()
        prefs = data.get("prefs", {}) or {}
        # reuse suggest to get items
        resp = suggest()
        if resp.status_code != 200:
            return resp
        items = resp.get_json().get("items", [])
        cards = []
        for it in items[:10]:
            if isinstance(it, str):
                cards.append({
                    "title": it,
                    "imageUrl": None,
                    "description": "",
                    "action": {"label": "Open", "url": None}
                })
            else:
                text = it.get("text", "")
                url = it.get("url")
                image = it.get("image") or it.get("poster")
                cards.append({
                    "title": text,
                    "imageUrl": image,
                    "description": category,
                    "action": {"label": "View", "url": url}
                })
        return jsonify({"cards": cards})
    except Exception as e:
        print("❌ suggest_cards error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/events_cards', methods=['POST'])
def events_cards():
    """
    Returns events as cards: [{title, imageUrl, description, action:{label,url}}]
    Mirrors /events but transforms items for easy SalesIQ display.
    """
    try:
        data = request.get_json(force=True)
        # reuse events to get items
        resp = events()
        if resp.status_code != 200:
            return resp
        items = resp.get_json().get("items", [])
        cards = []
        for it in items[:10]:
            if isinstance(it, str):
                cards.append({
                    "title": it,
                    "imageUrl": None,
                    "description": "Event",
                    "action": {"label": "Open", "url": None}
                })
            else:
                text = it.get("text", "")
                url = it.get("url")
                cards.append({
                    "title": text,
                    "imageUrl": None,
                    "description": "Event",
                    "action": {"label": "Tickets", "url": url}
                })
        return jsonify({"cards": cards})
    except Exception as e:
        print("❌ events_cards error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/oauth/spotify/start')
def spotify_start():
    """
    Redirect user to Spotify authorization page.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_REDIRECT_URI:
        return "Spotify OAuth not configured", 400
    scope = "user-read-email"
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(SPOTIFY_REDIRECT_URI, safe='')}"
        f"&scope={requests.utils.quote(scope, safe='')}"
        f"&state=zo_rek_state"
    )
    return jsonify({"auth_url": auth_url})

@app.route('/oauth/spotify/callback')
def spotify_callback():
    """
    Handle Spotify authorization callback; exchange code for access token.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not SPOTIFY_REDIRECT_URI:
        return "Spotify OAuth not configured", 400
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    try:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers, timeout=10)
        tok = r.json()
        if "access_token" in tok:
            set_spotify_token(tok["access_token"], tok.get("expires_in", 3600))
            return "Spotify connected. You can close this window."
        return jsonify(tok), 400
    except Exception as e:
        print("❌ Spotify callback error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

@app.route('/ai_commentary', methods=['POST'])
def ai_commentary():
    """
    Optional AI commentary that crafts a fun blurb around provided items.
    Expects: { movie: {text}, song: {text}, food: {text}, mood }
    """
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "OPENAI_API_KEY not configured"}), 400
        data = request.get_json(force=True)
        movie = (data.get("movie") or {}).get("text", "")
        song = (data.get("song") or {}).get("text", "")
        food = (data.get("food") or {}).get("text", "")
        mood = data.get("mood", "")
        prompt = (
            "Write a short (40-70 words) playful recommendation combining a movie, a song, and a dish. "
            "Keep it upbeat and tailored to the user's mood.\n"
            f"Mood: {mood}\nMovie: {movie}\nSong: {song}\nFood: {food}\n"
        )
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a witty entertainment concierge."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers, timeout=20)
        out = r.json()
        text = (((out.get("choices") or [])[0] or {}).get("message") or {}).get("content", "").strip()
        return jsonify({"commentary": text or "Enjoy your picks!"})
    except Exception as e:
        print("❌ AI commentary error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400


# ====== GLOBAL ERROR HANDLERS ======
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found", "status": 404}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
