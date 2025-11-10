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
# ====================


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
        choice = str(data.get("choice", "")).strip().lower()
        genre = str(data.get("genre", "random")).strip().lower()
        mood = str(data.get("mood", "")).strip()
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip()

        suggestion = "No suggestion found."

        # ====== Smart Category Handling ======
        if "movie" in choice:
            try:
                url = f"https://www.omdbapi.com/?apikey={OMDB_KEY}&s={genre}"
                res = requests.get(url, timeout=8).json()
                if res.get("Search"):
                    result = random.choice(res["Search"])
                    suggestion = f"🎬 {result.get('Title', 'Unknown')} ({result.get('Year', 'N/A')})"
            except Exception as e:
                suggestion = f"⚠️ Movie API error: {str(e)}"

        elif "book" in choice:
            try:
                url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{genre}"
                res = requests.get(url, timeout=8).json()
                if "items" in res:
                    result = random.choice(res["items"])
                    title = result.get("volumeInfo", {}).get("title", "Unknown Title")
                    suggestion = f"📚 {title}"
            except Exception as e:
                suggestion = f"⚠️ Book API error: {str(e)}"

        elif "food" in choice or "recipe" in choice:
            try:
                url = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
                res = requests.get(url, timeout=8).json()
                if "recipes" in res:
                    recipe = res["recipes"][0]
                    suggestion = f"🍕 {recipe.get('title', 'Unknown Recipe')}"
            except Exception as e:
                suggestion = f"⚠️ Food API error: {str(e)}"

        else:
            suggestion = "Please choose from Movies, Books, or Food."

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


# ====== GLOBAL ERROR HANDLERS ======
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found", "status": 404}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
