# app/middlewares/__init__.py
from flask import jsonify
from werkzeug.exceptions import HTTPException
from app.utils.responses import error_response


def register_middlewares(app):

    @app.before_request
    def log_request():
        print(f"[REQ] {app.name}: {app.request_class}")

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return error_response(message=e.description, status=e.code)
        return error_response(message=str(e), status=500)
