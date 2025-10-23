from app import create_app, db
from app.models import Era

app = create_app()
with app.app_context():
    default = [
        ("Colonial", "Colonial era description"),
        ("Post-Independence", "Post-Independence era description"),
        ("Present-Day", "Present-Day era description"),
        ("Futuristic", "Futurescape era description"),
    ]
    for name, desc in default:
        if not Era.query.filter_by(name=name).first():
            db.session.add(Era(name=name, description=desc))
    db.session.commit()
    print("Eras seeded.")
