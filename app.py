from flask import Flask, request, jsonify, render_template
import requests, datetime, random

app = Flask(__name__)


OMDB_KEY = "24b393c0"
SPOONACULAR_KEY = "7a3b4893233c41d3b327eacdba876813"
SHEET_BEST_URL = "https://api.sheetbest.com/sheets/766d80b7-7fbe-4480-b3d1-6b44795a9cef"


@app.route('/')
def home():
    return render_template("index.html")

@app.route('/zorek', methods=['HEAD'])
def zorek_head():
    return '', 200


@app.route('/zorek', methods=['POST'])
def zorek():
    try:
        data = request.get_json()
        choice = data.get("choice")
        genre = data.get("genre", "random")
        mood = data.get("mood", "")
        name = data.get("name", "")
        email = data.get("email", "")

        suggestion = "No suggestion found."

        if choice == "Movies":
            url = f"https://www.omdbapi.com/?apikey={OMDB_KEY}&s={genre}"
            res = requests.get(url).json()
            if res.get("Search"):
                result = random.choice(res["Search"])
                suggestion = f"🎬 {result['Title']} ({result['Year']})"
        
        elif choice == "Books":
            url = f"https://www.googleapis.com/books/v1/volumes?q=subject:{genre}"
            res = requests.get(url).json()
            if "items" in res:
                result = random.choice(res["items"])
                title = result["volumeInfo"]["title"]
                suggestion = f"📚 {title}"
        
        elif choice == "Food":
            url = f"https://api.spoonacular.com/recipes/random?apiKey={SPOONACULAR_KEY}&number=1"
            res = requests.get(url).json()
            if "recipes" in res:
                recipe = res["recipes"][0]
                suggestion = f"🍕 {recipe['title']}"

        # ====== Log interaction to Google Sheets ======
        log = {
            "Name": name,
            "Email": email,
            "Choice": choice,
            "Genre": genre,
            "Mood": mood,
            "Suggestion": suggestion,
            "Timestamp": str(datetime.datetime.now())
        }
        requests.post(SHEET_BEST_URL, json=log)
        # ==============================================

        return jsonify({"suggestion": suggestion})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
