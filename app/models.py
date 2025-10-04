from app import db
from datetime import datetime, timedelta


# ---- USERS ----
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    fullname = db.Column(db.String, nullable=False, index=True)  # useful for login
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String, unique=True, index=True, nullable=False)
    nationality = db.Column(db.String, nullable=False)
    referral = db.Column(db.String, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255))
    home_era = db.Column(db.String(50))
    role = db.Column(db.String(20), default="user")  # user, moderator, admin
    points = db.Column(db.Integer, default=0)
    provider = db.Column(db.String, default="local")
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(128), nullable=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    missions = db.relationship(
        "MissionParticipant", back_populates="user", cascade="all, delete-orphan"
    )
    badges = db.relationship("UserBadge", backref="user", cascade="all, delete-orphan")
    events = db.relationship("Event", backref="creator", cascade="all, delete-orphan")
    rsvps = db.relationship("RSVP", backref="user", cascade="all, delete-orphan")


# class PasswordResetOTP(db.Model):
#     __tablename__ = "password_reset_otps"

#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(120), nullable=False)
#     otp = db.Column(db.String(6), nullable=False)
#     expiry = db.Column(db.DateTime, nullable=False)
#     is_verified = db.Column(db.Boolean, default=False)
#     request_count = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     def is_expired(self):
#         return datetime.utcnow() > self.expiry


class PasswordResetOTP(db.Model):
    __tablename__ = "password_reset_otps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # NEW
    otp = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(50), default="password_reset")  # NEW
    expires_at = db.Column(db.DateTime, nullable=False)  # renamed from expiry
    is_verified = db.Column(db.Boolean, default=False)
    request_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="otps")  # NEW relationship

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ---- COMMUNITY ----
class Era(db.Model):
    __tablename__ = "eras"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    zones = db.relationship("Zone", backref="era", cascade="all, delete-orphan")


class Zone(db.Model):
    __tablename__ = "zones"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    era_id = db.Column(db.Integer, db.ForeignKey("eras.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pinned = db.Column(db.Boolean, default=False)
    hot_thread = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), default="post")  # "post" or "comment"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)


# ---- FEEDBACK ----
class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # "upvote" or "downvote"
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=True)
    parent = db.relationship("Feedback", remote_side=[id], backref="replies")


# ---- EVENTS ----
event_participants = db.Table(
    "event_participants",
    db.Column("event_id", db.Integer, db.ForeignKey("events.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
)

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rsvps = db.relationship("RSVP", backref="event", cascade="all, delete-orphan")

    participants = db.relationship(
        "User", secondary=event_participants, backref="joined_events"
    )


class RSVP(db.Model):
    __tablename__ = "rsvps"
    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event_rsvp"),
    )

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)  # going, interested, not_going
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

# ---- GAMIFICATION ----
class Badge(db.Model):
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    icon = db.Column(db.String(255))  # optional: link to image


class UserBadge(db.Model):
    __tablename__ = "user_badges"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"))


class Mission(db.Model):
    __tablename__ = "missions"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, default=0)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)

    # Link mission to a badge (optional, some missions may not give badges)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=True)
    badge = db.relationship("Badge", backref="missions")

    # Track participants
    participants = db.relationship("MissionParticipant", back_populates="mission")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MissionParticipant(db.Model):
    __tablename__ = "mission_participants"

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(50), default="joined")  # joined | completed
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    mission = db.relationship("Mission", back_populates="participants")
    user = db.relationship("User", back_populates="missions")


class FeedbackVote(db.Model):
    __tablename__ = "feedback_votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # "upvote" or "downvote"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships (optional but useful)
    user = db.relationship("User", backref="feedback_votes", lazy=True)
    feedback = db.relationship("Feedback", backref="votes", lazy=True)

    def __repr__(self):
        return f"<FeedbackVote {self.vote_type} by User {self.user_id} on Feedback {self.feedback_id}>"


# class UserMission(db.Model):
#     __tablename__ = "user_missions"
#     id = db.Column(db.Integer, primary_key=True)
#     status = db.Column(db.String(20), default="in_progress")  # in_progress, completed
#     completed_at = db.Column(db.DateTime)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)

#     __table_args__ = (
#         db.UniqueConstraint("user_id", "mission_id", name="unique_user_mission"),
#     )
