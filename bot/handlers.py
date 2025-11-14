"""
Bot Handlers - Logic for processing Zoho SalesIQ bot requests
"""

import requests
import datetime
import traceback
from typing import Dict, List, Any


def log_to_sheet(sheet_url: str, endpoint_name: str, data: dict):
    """Log interaction to Google Sheet via Sheet.best"""
    if not sheet_url:
        return
    try:
        log_entry = {
            "Endpoint": endpoint_name,
            "Name": data.get("name", data.get("Name", "Unknown")),
            "Email": data.get("email", data.get("Email", "")),
            "Choice": data.get("choice", data.get("Choice", "")),
            "Genre": data.get("genre", data.get("Genre", "")),
            "Mood": data.get("mood", data.get("Mood", "")),
            "Suggestion": data.get("suggestion", data.get("Suggestion", "")),
            "Timestamp": datetime.datetime.utcnow().isoformat()
        }
        requests.post(sheet_url, json=log_entry, timeout=5)
    except Exception as e:
        print(f"⚠️ Logging to sheet failed for {endpoint_name}: {e}")


def format_salesiq_card(item: Dict[str, Any], category: str) -> Dict[str, Any]:
    """
    Transform an item dict into Zoho SalesIQ card format.
    
    Args:
        item: Dict with keys like "text", "url", "image", "poster"
        category: Category name (movies, books, games, music, food)
    
    Returns:
        Dict in SalesIQ card format: {title, imageUrl, description, action: {label, url}}
    """
    text = item.get("text", "")
    url = item.get("url")
    image = item.get("image") or item.get("poster")
    
    # Extract title and description
    title = text
    description = category.title()
    action_label = "View"
    action_url = url
    
    # Clean emojis
    emoji_map = {"🎬": "", "📚": "", "🎮": "", "🎵": "", "🍕": "", "🎟️": ""}
    for emoji, replacement in emoji_map.items():
        title = title.replace(emoji, "")
    
    # Category-specific formatting
    if category == "movies" and "⭐" in text:
        parts = text.split("—")
        if len(parts) > 1:
            title_part = parts[0].strip()
            rating_part = parts[1].strip()
            title = title_part.replace("🎬", "").strip()
            description = rating_part if "⭐" in rating_part else f"Movie | {category.title()}"
        
        # Add streaming platform links for movies
        movie_title_clean = title.split("(")[0].strip() if "(" in title else title.strip()
        if movie_title_clean:
            justwatch_url = f"https://www.justwatch.com/in/search?q={requests.utils.quote(movie_title_clean)}"
            action_url = justwatch_url if movie_title_clean else (url if url and "imdb.com" in url else url)
            action_label = "Watch Now"
            description = f"{description} | Available on Netflix, Prime, Disney+"
    elif category == "books" and " — " in title:
        parts = title.split(" — ")
        if len(parts) > 1:
            title = parts[0].strip()
            author = parts[1].strip()
            description = f"Book by {author}"
            book_title_clean = requests.utils.quote(title)
            goodreads_url = f"https://www.goodreads.com/search?q={book_title_clean}"
            action_url = goodreads_url
            action_label = "Read More"
    elif category == "games":
        title = text.replace("🎮", "").strip()
        if "—" in title:
            title = title.split("—")[0].strip()
        game_title_clean = requests.utils.quote(title)
        steam_url = f"https://store.steampowered.com/search/?term={game_title_clean}"
        action_url = steam_url
        action_label = "Buy Game"
        description = "Game"
    elif category == "music":
        title = text.replace("🎵", "").strip()
        if "—" in title:
            title = title.split("—")[0].strip()
        action_label = "Listen"
        description = "Music"
    elif category == "food":
        title = text.replace("🍕", "").strip()
        action_label = "View Recipe"
        description = "Recipe"
    else:
        # Clean up title
        if "—" in title:
            title = title.split("—")[0].strip()
        title = title.strip()
    
    return {
        "title": title[:100],  # Limit title length
        "imageUrl": image if image else None,
        "description": description[:200],  # Limit description length
        "action": {
            "label": action_label if action_url else "N/A",
            "url": action_url if action_url else None
        }
    }


def format_event_card(item: Dict[str, Any], category: str, city: str) -> Dict[str, Any]:
    """
    Transform an event item into Zoho SalesIQ card format.
    
    Args:
        item: Dict with keys like "text", "url", "image", "poster"
        category: Event category (movies, concerts, talkshow, etc.)
        city: City name
    
    Returns:
        Dict in SalesIQ card format
    """
    text = item.get("text", "")
    url = item.get("url")
    image = item.get("image") or item.get("poster")
    title = text.replace("🎟️", "").strip()
    
    # Clean up title
    if "—" in title:
        title = title.split("—")[0].strip()
    
    # Better description based on category
    if category == "movies":
        description = f"Now Playing in {city} | Book tickets on BookMyShow"
        action_label = "Book Tickets"
    elif category == "concerts":
        description = f"Concert in {city} | Book tickets"
        action_label = "Book Tickets"
    elif category == "talkshow":
        description = f"Talk Show in {city} | Book tickets"
        action_label = "Book Tickets"
    else:
        description = f"Event in {city}"
        action_label = "Book Tickets"
    
    return {
        "title": title,
        "imageUrl": image if image else None,
        "description": description,
        "action": {
            "label": action_label if url else "View",
            "url": url if url else None
        }
    }

