"""
Widget Routes - Zoho SalesIQ Operator Widget Endpoints
"""

from flask import request, jsonify
import datetime
import traceback


def create_widget_routes(
    app,
    spotify_token_valid_func
):
    """
    Create and register widget routes.
    
    Args:
        app: Flask app instance
        spotify_token_valid_func: Function to check Spotify token validity
    """
    
    @app.route('/widget_detail', methods=['GET'])
    def widget_detail():
        """
        SalesIQ Operator Widget endpoint.
        Returns visitor data in Zoho widget_detail format.
        Query params: email (optional, defaults to demo@zorek.ai)
        
        This endpoint is called by Zoho SalesIQ to display visitor information
        in the operator chat window.
        """
        try:
            email = request.args.get("email", "demo@zorek.ai")
            
            # In a real implementation, you'd fetch this from your database/Sheet
            # For now, return mock data structure matching Zoho widget_detail format
            visitor_data = {
                "visitor_email": email,
                "last_action": "Requested Movie Suggestions",
                "preferred_genre": "Action",
                "spotify_status": "Connected" if spotify_token_valid_func() else "Not connected",
                "lastChoice": "Movies",
                "lastGenre": "Action",
                "lastSuggestion": "Inception (2010)",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "interactionCount": 1
            }
            
            return jsonify(visitor_data)
        except Exception as e:
            print("❌ Widget detail error:", traceback.format_exc())
            return jsonify({"error": str(e)}), 400


def register_widget_routes(app, **kwargs):
    """Register all widget routes with the Flask app"""
    create_widget_routes(app, **kwargs)

