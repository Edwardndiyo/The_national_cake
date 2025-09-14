# app/utils/responses.py
from flask import jsonify


def success_response(data=None, message="Success", status=200):
    return jsonify({"status": "success", "message": message, "data": data}), status


def error_response(message="An error occurred", status=400, errors=None):
    return jsonify({"status": "error", "message": message, "errors": errors}), status
