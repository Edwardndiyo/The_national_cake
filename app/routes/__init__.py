from flask import Blueprint

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return {"Paradox": "Hello Flask Backend!"}


def init_routes(app):
    app.register_blueprint(main)
