"""
ZoRek Bot Module - Zoho SalesIQ Integration
Contains all endpoints and handlers for Zoho SalesIQ chat bot integration.
"""

from .routes import register_bot_routes, create_bot_routes
from .widgets import register_widget_routes, create_widget_routes
from .handlers import log_to_sheet, format_salesiq_card, format_event_card

__all__ = [
    'register_bot_routes',
    'register_widget_routes',
    'create_bot_routes',
    'create_widget_routes',
    'log_to_sheet',
    'format_salesiq_card',
    'format_event_card'
]

