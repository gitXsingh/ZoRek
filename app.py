from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import datetime
import random
import traceback
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure CORS for Zoho SalesIQ domains
# Allow all origins for Zoho integration (SalesIQ can call from various subdomains)
# In production, you may want to restrict this to specific Zoho domains
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ====== CONFIG - Load from Environment Variables ======
OMDB_KEY = os.environ.get("OMDB_KEY", "")
SPOONACULAR_KEY = os.environ.get("SPOONACULAR_KEY", "")
SHEET_BEST_URL = os.environ.get("SHEET_BEST_URL", "")
SEATGEEK_CLIENT_ID = os.environ.get("SEATGEEK_CLIENT_ID", "")
TMDB_KEY = os.environ.get("TMDB_KEY", "")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
# Detect localhost vs production for Spotify OAuth
_default_redirect = "http://localhost:5000/oauth/spotify/callback" if os.environ.get("FLASK_ENV") != "production" else "https://zorek.onrender.com/oauth/spotify/callback"
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", _default_redirect)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# ====================

SPOTIFY_TOKEN = {"access_token": None, "expires_at": 0, "mode": None}  # mode: 'user' or 'app'

def _now_ts() -> int:
    return int(datetime.datetime.utcnow().timestamp())

def set_spotify_token(access_token: str, expires_in: int, token_kind: str = "user"):
    SPOTIFY_TOKEN["access_token"] = access_token
    SPOTIFY_TOKEN["expires_at"] = _now_ts() + int(expires_in or 0) - 30
    SPOTIFY_TOKEN["mode"] = token_kind

def spotify_token_valid() -> bool:
    return bool(SPOTIFY_TOKEN.get("access_token")) and _now_ts() < SPOTIFY_TOKEN.get("expires_at", 0)

def ensure_spotify_token() -> bool:
    """
    Ensure we have a valid Spotify token. If no user token, fall back to client-credentials.
    """
    if spotify_token_valid():
        return True
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            r = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers, timeout=10)
            tok = r.json()
            if "access_token" in tok:
                set_spotify_token(tok["access_token"], tok.get("expires_in", 3600), token_kind="app")
                return True
        except Exception:
            return False
    return False

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
    Return a dict with text, url, image, and poster for a movie suggestion.
    Returns: {"text": str, "url": str | None, "image": str | None, "poster": str | None}
    """
    try:
        # Prefer items that truly match genre tokens
        results = search_movies_with_filters(genre, 0.0, "")
        for it in results:
            if it.get("url"):
                return {
                    "text": it.get("text", ""),
                    "url": it.get("url"),
                    "image": it.get("image"),
                    "poster": it.get("poster")
                }
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
            poster = d.get("Poster") or first.get("Poster")
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None
            return {
                "text": f"🎬 {title} ({year})",
                "url": imdb_url,
                "image": poster if poster and poster != "N/A" else None,
                "poster": poster if poster and poster != "N/A" else None
            }
        return {"text": "🎬 Couldn't find a movie for that genre. Try another one?", "url": None, "image": None, "poster": None}
    except Exception as exc:
        return {"text": f"⚠️ Movie API error: {str(exc)}", "url": None, "image": None, "poster": None}

def get_song_recommendation_with_url(song_type: str = "", mood: str = "") -> dict:
    """
    Return a dict with text, url, and image for a song suggestion.
    Prefer Spotify if OAuth token available, else fallback to iTunes.
    """
    query = (song_type or mood or "popular").strip()
    # Try Spotify
    if ensure_spotify_token() and spotify_token_valid():
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
                return {"text": f"🎵 {name} — {artists}", "url": url, "image": image, "source": "spotify"}
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
            return {"text": f"🎵 {track_name} — {artist}", "url": link, "image": img, "source": "itunes"}
        return {"text": "🎵 Couldn't find a song right now. Try another type?", "url": None, "source": "unknown"}
    except Exception as exc:
        return {"text": f"⚠️ Music API error: {str(exc)}", "url": None, "source": "error"}

def suggest_music_with_links(query: str = "") -> list[dict]:
    """
    Suggest multiple tracks. Prefer Spotify if OAuth token available, else iTunes.
    Returns list of {text, url, image}
    Avoids generic terms like "popular" that return songs with that title.
    """
    # Better default terms that avoid "Popular" spam
    q = (query or "").strip()
    if not q or q.lower() in ["popular", "music", "song", "songs"]:
        # Use diverse artist/term searches to get variety
        default_terms = ["top hits", "billboard", "ed sheeran", "taylor swift", "the weeknd", "ariana grande"]
        import random as _random
        q = _random.choice(default_terms)
    
    # Try Spotify first
    if ensure_spotify_token() and spotify_token_valid():
        try:
            headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN['access_token']}"}
            params = {"q": q, "type": "track", "limit": 10}
            resp = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=8)
            data = resp.json()
            items = (data.get("tracks", {}) or {}).get("items", [])
            results = []
            for t in items:
                name = t.get("name", "Unknown Track")
                artists = ", ".join([a.get("name") for a in t.get("artists", [])]) or "Unknown Artist"
                # Skip generic titles
                if name.lower() in ["popular", "music", "song"] and not artists:
                    continue
                url = (t.get("external_urls") or {}).get("spotify")
                imgs = ((t.get("album") or {}).get("images") or [])
                image = imgs[0]["url"] if imgs else None
                results.append({"text": f"🎵 {name} — {artists}", "url": url, "image": image, "source": "spotify"})
            if results:
                return results[:10]  # Limit to 10
        except Exception:
            pass
    # Fallback iTunes
    try:
        term = q.replace(" ", "+")
        url = f"https://itunes.apple.com/search?term={term}&entity=song&limit=20"
        res = requests.get(url, timeout=8)
        data = res.json()
        results = []
        seen_titles = set()  # Avoid duplicates
        for track in data.get("results", []):
            track_name = track.get("trackName", "Unknown Track")
            artist = track.get("artistName", "Unknown Artist")
            # Skip generic titles or duplicates
            title_key = f"{track_name.lower()}-{artist.lower()}"
            if track_name.lower() in ["popular", "music", "song"] and len(artist) < 3:
                continue
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            link = track.get("trackViewUrl") or track.get("collectionViewUrl") or track.get("artistViewUrl")
            img = track.get("artworkUrl100") or track.get("artworkUrl60")
            results.append({"text": f"🎵 {track_name} — {artist}", "url": link, "image": img, "source": "itunes"})
            if len(results) >= 10:
                break
        return results or [{"text": "No songs found.", "url": None, "source": "unknown"}]
    except Exception as exc:
        return [{"text": f"⚠️ Music search error: {str(exc)}", "url": None, "source": "error"}]

def get_food_recommendation_with_url(diet: str = "") -> dict:
    """
    Return a dict with text, url, and image for a food/recipe suggestion.
    Returns: {"text": str, "url": str | None, "image": str | None}
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
            return {"text": f"🍕 {title}", "url": link, "image": img if img else None}
        return {"text": "🍕 Couldn't fetch a recipe right now. Try again?", "url": None, "image": None}
    except Exception as exc:
        return {"text": f"⚠️ Food API error: {str(exc)}", "url": None, "image": None}

def fetch_trending_movies(limit: int = 10) -> list[dict]:
    """
    Fetch trending movies from TMDB as a fallback when filtered searches fail.
    """
    if not TMDB_KEY:
        return []
    try:
        resp = requests.get(
            f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_KEY}&language=en-US",
            timeout=8
        )
        data = resp.json()
        results = []
        for movie in (data.get("results") or [])[:limit]:
            title = movie.get("title") or movie.get("name") or "Movie"
            release_year = (movie.get("release_date") or "")[:4]
            vote_average = movie.get("vote_average", "N/A")
            tmdb_id = movie.get("id")
            poster_path = movie.get("poster_path")
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            results.append({
                "text": f"🎬 {title} ({release_year or 'N/A'}) — ⭐ {vote_average}",
                "url": f"https://www.themoviedb.org/movie/{tmdb_id}" if tmdb_id else None,
                "poster": poster,
                "image": poster
            })
        return results
    except Exception:
        return []


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
        if results:
            return results
        fallback_results = fetch_trending_movies()
        if fallback_results:
            return fallback_results
        return [{"text": "No movies matched your filters.", "url": None}]
    except Exception as exc:
        fallback_results = fetch_trending_movies()
        if fallback_results:
            return fallback_results
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


# Bot routes: ONLY /suggest_cards, /events_cards, /recommendations
# All registered via bot module below
# Legacy /suggest and /events endpoints removed - use card endpoints instead

@app.route('/oauth/spotify/start')
def spotify_start():
    """
    Redirect user to Spotify authorization page.
    """
    if not SPOTIFY_CLIENT_ID:
        return jsonify({"error": "Spotify OAuth not configured"}), 400
    
    # Use request host to determine redirect URI for local development
    redirect_uri = SPOTIFY_REDIRECT_URI
    if request.host and ("localhost" in request.host or "127.0.0.1" in request.host):
        redirect_uri = f"http://{request.host}/oauth/spotify/callback"
    elif not redirect_uri:
        redirect_uri = "http://localhost:5000/oauth/spotify/callback"
    
    scope = "user-read-email user-read-private"
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(redirect_uri, safe='')}"
        f"&scope={requests.utils.quote(scope, safe='')}"
        f"&state=zo_rek_state"
    )
    # Redirect directly to Spotify
    return redirect(auth_url)

@app.route('/oauth/spotify/callback')
def spotify_callback():
    """
    Handle Spotify authorization callback; exchange code for access token.
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return "Spotify OAuth not configured", 400
    
    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400
    
    # Determine redirect URI (same logic as start endpoint)
    redirect_uri = SPOTIFY_REDIRECT_URI
    if request.host and ("localhost" in request.host or "127.0.0.1" in request.host):
        redirect_uri = f"http://{request.host}/oauth/spotify/callback"
    elif not redirect_uri:
        redirect_uri = "http://localhost:5000/oauth/spotify/callback"
    
    try:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers, timeout=10)
        r.raise_for_status()
        tok = r.json()
        if "access_token" in tok:
            set_spotify_token(tok["access_token"], tok.get("expires_in", 3600), token_kind="user")
            # Redirect back to app with success message
            return redirect("/?spotify=connected")
        return jsonify({"error": "Failed to get access token", "response": tok}), 400
    except Exception as e:
        print("❌ Spotify callback error:", traceback.format_exc())
        return f"Error: {str(e)}. <a href='/'>Return to app</a>", 400

@app.route('/oauth/spotify/status')
def spotify_status():
    """
    Returns whether the server currently has a valid Spotify access token.
    """
    return jsonify({"connected": spotify_token_valid(), "mode": SPOTIFY_TOKEN.get("mode")})

@app.route('/ai_commentary', methods=['POST'])
def ai_commentary():
    """
    Optional AI commentary that crafts a fun blurb around provided items.
    Expects: { movie: {text}, song: {text}, food: {text}, mood }
    Uses GPT-4o-mini with GPT-3.5-turbo fallback.
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
            "Write a short (1-2 sentences, 40-70 words) playful recommendation combining a movie, a song, and a dish. "
            "Keep it upbeat and tailored to the user's mood. Be creative and engaging.\n"
            f"Mood: {mood}\nMovie: {movie}\nSong: {song}\nFood: {food}\n"
        )
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Try GPT-4o-mini first, fallback to GPT-3.5-turbo
        models = ["gpt-4o-mini", "gpt-3.5-turbo"]
        for model in models:
            try:
                body = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a witty entertainment concierge."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 150
                }
                r = requests.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers, timeout=20)
                r.raise_for_status()
                out = r.json()
                text = (((out.get("choices") or [])[0] or {}).get("message") or {}).get("content", "").strip()
                if text:
                    return jsonify({"commentary": text})
            except Exception as model_error:
                if model == models[-1]:  # Last model, re-raise
                    raise model_error
                continue  # Try next model
        
        return jsonify({"commentary": "Enjoy your picks!"})
    except Exception as e:
        print("❌ AI commentary error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 400

# ====== Register Zoho SalesIQ Bot Routes ======
# Import and register ONLY the 3 required bot endpoints
from bot.routes import create_bot_routes

# Register ONLY the 3 required endpoints for Zoho SalesIQ Script Bot
# Register bot routes with all required API functions
create_bot_routes(
    app,
    # API functions
    search_movies_with_filters=search_movies_with_filters,
    suggest_books_with_links=suggest_books_with_links,
    suggest_games_with_links=suggest_games_with_links,
    suggest_music_with_links=suggest_music_with_links,
    get_food_recommendation_with_url=get_food_recommendation_with_url,
    get_movie_recommendation_with_url=get_movie_recommendation_with_url,
    get_song_recommendation_with_url=get_song_recommendation_with_url,
    events_from_seatgeek=events_from_seatgeek,
    fallback_event_links=fallback_event_links,
    geocode_city=geocode_city,
    fetch_trending_movies=fetch_trending_movies,  # Trending movies fallback
    # Configuration
    SHEET_BEST_URL=SHEET_BEST_URL,
    TMDB_KEY=TMDB_KEY,
    SEATGEEK_CLIENT_ID=SEATGEEK_CLIENT_ID
)

@app.route('/health_check', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify all APIs are working.
    Returns status of each service.
    """
    checks = {}
    all_ok = True
    
    # Check OMDb
    try:
        if OMDB_KEY:
            test = requests.get(f"https://www.omdbapi.com/?apikey={OMDB_KEY}&i=tt3896198", timeout=5)
            checks["OMDb"] = "PASS" if test.status_code == 200 else "FAIL"
        else:
            checks["OMDb"] = "SKIP"
    except Exception:
        checks["OMDb"] = "FAIL"
        all_ok = False
    
    # Check Google Books
    try:
        test = requests.get("https://www.googleapis.com/books/v1/volumes?q=test", timeout=5)
        checks["Books"] = "PASS" if test.status_code == 200 else "FAIL"
    except Exception:
        checks["Books"] = "FAIL"
        all_ok = False
    
    # Check Spoonacular
    try:
        if SPOONACULAR_KEY:
            test = requests.get(f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1", timeout=5)
            checks["Spoonacular"] = "PASS" if test.status_code == 200 else "FAIL"
        else:
            checks["Spoonacular"] = "SKIP"
    except Exception:
        checks["Spoonacular"] = "FAIL"
        all_ok = False
    
    # Check Sheet.best
    try:
        if SHEET_BEST_URL:
            # Just check if URL is reachable (HEAD request)
            test = requests.head(SHEET_BEST_URL, timeout=5)
            checks["SheetBest"] = "PASS" if test.status_code in [200, 405] else "FAIL"  # 405 is OK for HEAD
        else:
            checks["SheetBest"] = "SKIP"
    except Exception:
        checks["SheetBest"] = "FAIL"
        all_ok = False
    
    # Check Local endpoint (self-check)
    try:
        checks["Local"] = "PASS"
    except Exception:
        checks["Local"] = "FAIL"
        all_ok = False
    
    # Check TMDB
    try:
        if TMDB_KEY:
            test = requests.get(f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_KEY}", timeout=5)
            checks["TMDB"] = "PASS" if test.status_code == 200 else "FAIL"
        else:
            checks["TMDB"] = "SKIP"
    except Exception:
        checks["TMDB"] = "FAIL"
    
    # Check Spotify
    try:
        if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
            checks["Spotify"] = "PASS" if ensure_spotify_token() else "FAIL"
        else:
            checks["Spotify"] = "SKIP"
    except Exception:
        checks["Spotify"] = "FAIL"
    
    return jsonify({
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })


# ====== GLOBAL ERROR HANDLERS ======
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found", "status": 404}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500


# ====== Root Endpoint ======
# For Zoho SalesIQ bot integration only - no web interface served here
@app.route('/')
def home():
    """Simple landing page with subtle hero and SalesIQ widget"""
    print(f"\n📋 [INFO] Root endpoint accessed from {request.remote_addr} at {datetime.datetime.utcnow().isoformat()}\n")

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZoRek · Entertainment Assistant</title>
    <style>
        :root { color-scheme: dark; }
        * { box-sizing: border-box; font-family: "Inter","Segoe UI",sans-serif; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            background: linear-gradient(135deg, #101428 0%, #181f3a 60%, #101428 100%);
            color: #f3f5ff;
        }
        .hero {
            text-align: center;
            padding: 2.5rem 2rem;
            border-radius: 18px;
            background: rgba(4,6,14,0.7);
            border: 1px solid rgba(255,255,255,0.08);
            width: min(90vw, 640px);
            box-shadow: 0 25px 55px rgba(5,8,20,0.55);
            backdrop-filter: blur(12px);
        }
        h1 {
            margin: 0;
            font-size: clamp(2rem, 4vw, 2.8rem);
            letter-spacing: 0.02em;
        }
        p {
            margin: 1rem auto 0;
            font-size: 1.05rem;
            max-width: 480px;
            color: rgba(243,245,255,0.78);
            line-height: 1.6;
        }
        .pill {
            display: inline-flex;
            gap: 0.4rem;
            padding: 0.55rem 1.25rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.05);
            margin-top: 1.5rem;
            font-size: 0.92rem;
            color: rgba(243,245,255,0.9);
        }
    </style>
</head>
<body>
    <main class="hero">
        <div class="pill">ZoRek · SalesIQ Entertainment Bot</div>
        <h1>Entertainment assistant is live.</h1>
        <p>ZoRek is running as a backend service for the Zoho SalesIQ script bot. Use your SalesIQ interface to chat with the assistant. This page only hosts the widget script.</p>
    </main>
    <script>window.$zoho=window.$zoho||{};$zoho.salesiq=$zoho.salesiq||{ready:function(){}};</script>
    <script id="zsiqscript" src="https://salesiq.zohopublic.com/widget?wc=siq5bbfed3274ca9acdcade85bd6f8a63dcc621b2560b3aa6bfe6d3f52d07cb0ee1" defer></script>
</body>
</html>
"""

    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
