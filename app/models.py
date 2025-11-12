from app import db
from datetime import datetime, timedelta


user_era_membership = db.Table(
    "user_era_membership",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("era_id", db.Integer, db.ForeignKey("eras.id"), primary_key=True),
    db.Column(
        "joined_at", db.DateTime, default=datetime.utcnow
    ),  # REMOVED the nested db.Column
)

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
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    missions = db.relationship(
        "MissionParticipant", back_populates="user", cascade="all, delete-orphan"
    )
    joined_eras = db.relationship(
        "Era",
        secondary=user_era_membership,
        back_populates="members",
    )
    badges = db.relationship("UserBadge", backref="user", cascade="all, delete-orphan")
    events = db.relationship("Event", backref="creator", cascade="all, delete-orphan")
    rsvps = db.relationship("RSVP", backref="user", cascade="all, delete-orphan")
    posts = db.relationship("Post", back_populates="user", cascade="all, delete-orphan")


class PasswordResetOTP(db.Model):
    __tablename__ = "password_reset_otps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(50), default="password_reset")
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    request_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="otps")

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ---- COMMUNITY ----
class Era(db.Model):
    __tablename__ = "eras"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    year_range = db.Column(db.String(50))
    image = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    zones = db.relationship("Zone", back_populates="era", cascade="all, delete-orphan")
    members = db.relationship(
        "User",
        secondary=user_era_membership,
        back_populates="joined_eras",
    )


class Zone(db.Model):
    __tablename__ = "zones"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    era_id = db.Column(db.Integer, db.ForeignKey("eras.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # FIX: Use back_populates instead of backref
    era = db.relationship("Era", back_populates="zones")
    posts = db.relationship("Post", back_populates="zone", cascade="all, delete-orphan")
    # era = db.relationship("Era", backref="zones", lazy=True)


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media = db.Column(db.Text, nullable=True)
    pinned = db.Column(db.Boolean, default=False)
    hot_thread = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)

    # ADD THIS RELATIONSHIP:
    # FIX: Use back_populates instead of backref
    user = db.relationship("User", back_populates="posts")
    zone = db.relationship("Zone", back_populates="posts")
    # user = db.relationship("User", backref="user_posts", lazy=True)
    # zone = db.relationship("Zone", backref="posts", lazy=True)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)


# class Like(db.Model):
#     __tablename__ = "likes"
#     id = db.Column(db.Integer, primary_key=True)
#     type = db.Column(db.String(20), default="post")
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
#     comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), default="post")  # "post" or "comment"
    reaction_type = db.Column(
        db.String(20), default="like"
    )  # "like" (agree) or "dislike" (disagree)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)

    # Add unique constraint to prevent duplicate reactions
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "post_id", "reaction_type", name="unique_user_post_reaction"
        ),
        db.UniqueConstraint(
            "user_id",
            "comment_id",
            "reaction_type",
            name="unique_user_comment_reaction",
        ),
    )


# ---- FEEDBACK ----
class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)
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
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)


# ---- GAMIFICATION ----
class Badge(db.Model):
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    icon = db.Column(db.String(255))


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

    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=True)
    badge = db.relationship("Badge", backref="missions")

    participants = db.relationship("MissionParticipant", back_populates="mission")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Idea(db.Model):
    __tablename__ = "ideas"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="submitted")
    validated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    points_awarded = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    mentor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class MissionParticipant(db.Model):
    __tablename__ = "mission_participants"

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(50), default="joined")
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    mission = db.relationship("Mission", back_populates="participants")
    user = db.relationship("User", back_populates="missions")


class FeedbackVote(db.Model):
    __tablename__ = "feedback_votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="feedback_votes", lazy=True)
    feedback = db.relationship("Feedback", backref="votes", lazy=True)

    def __repr__(self):
        return f"<FeedbackVote {self.vote_type} by User {self.user_id} on Feedback {self.feedback_id}>"


# ---- POLLS - FIXED SECTION ----
class Poll(db.Model):
    __tablename__ = "polls"
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # FIXED: Use back_populates and remove conflicting relationships
    options = db.relationship(
        "PollOption",
        back_populates="poll",
        cascade="all, delete-orphan",
        overlaps="votes,direct_votes",
    )

    # FIXED: Single relationship for votes with proper configuration
    votes = db.relationship(
        "PollVote",
        back_populates="poll",
        cascade="all, delete-orphan",
        viewonly=False,  # This is writable
    )


class PollOption(db.Model):
    __tablename__ = "poll_options"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    votes_count = db.Column(db.Integer, default=0)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)

    # FIXED: Use back_populates for consistency
    poll = db.relationship("Poll", back_populates="options")

    # Relationship to votes
    votes = db.relationship(
        "PollVote", back_populates="option", cascade="all, delete-orphan"
    )


class PollVote(db.Model):
    __tablename__ = "poll_votes"
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "poll_id", name="unique_user_poll_vote"),
    )

    # FIXED: Use back_populates instead of backref for clarity
    user = db.relationship("User", backref="poll_votes")

    # FIXED: Single relationship to poll with overlaps to resolve conflicts
    poll = db.relationship(
        "Poll", back_populates="votes", overlaps="direct_votes,votes"
    )

    option = db.relationship("PollOption", back_populates="votes")

    def __repr__(self):
        return f"<PollVote user_id={self.user_id} poll_id={self.poll_id} option_id={self.option_id}>"


# Add to your models.py
class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="unique_user_post_bookmark"),
    )

    # Relationships
    user = db.relationship("User", backref="bookmarks")
    post = db.relationship("Post", backref="bookmarked_by")


# from app import db
# from datetime import datetime, timedelta


# user_era_membership = db.Table(
#     "user_era_membership",
#     db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
#     db.Column("era_id", db.Integer, db.ForeignKey("eras.id"), primary_key=True),
#     db.Column("joined_at", db.DateTime, default=datetime.utcnow),
# )

# # ---- USERS ----
# class User(db.Model):
#     __tablename__ = "users"

#     id = db.Column(db.Integer, primary_key=True)
#     firstname = db.Column(db.String, nullable=False)
#     lastname = db.Column(db.String, nullable=False)
#     fullname = db.Column(db.String, nullable=False, index=True)  # useful for login
#     username = db.Column(db.String(50), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     phone = db.Column(db.String, unique=True, index=True, nullable=False)
#     nationality = db.Column(db.String, nullable=False)
#     referral = db.Column(db.String, nullable=True)
#     password_hash = db.Column(db.String(255), nullable=False)
#     avatar = db.Column(db.String(255))
#     home_era = db.Column(db.String(50))
#     role = db.Column(db.String(20), default="user")  # user, moderator, admin
#     points = db.Column(db.Integer, default=0)
#     provider = db.Column(db.String, default="local")
#     is_verified = db.Column(db.Boolean, default=False)
#     verification_token = db.Column(db.String(128), nullable=True)
#     firebase_uid = db.Column(db.String(128), unique=True, nullable=True)
#     last_login = db.Column(db.DateTime)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relationships
#     missions = db.relationship(
#         "MissionParticipant", back_populates="user", cascade="all, delete-orphan"
#     )
#     joined_eras = db.relationship(
#         "Era",
#         secondary=user_era_membership,
#         back_populates="members",
#     )
#     badges = db.relationship("UserBadge", backref="user", cascade="all, delete-orphan")
#     events = db.relationship("Event", backref="creator", cascade="all, delete-orphan")
#     rsvps = db.relationship("RSVP", backref="user", cascade="all, delete-orphan")


# # class PasswordResetOTP(db.Model):
# #     __tablename__ = "password_reset_otps"

# #     id = db.Column(db.Integer, primary_key=True)
# #     email = db.Column(db.String(120), nullable=False)
# #     otp = db.Column(db.String(6), nullable=False)
# #     expiry = db.Column(db.DateTime, nullable=False)
# #     is_verified = db.Column(db.Boolean, default=False)
# #     request_count = db.Column(db.Integer, default=0)
# #     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# #     def is_expired(self):
# #         return datetime.utcnow() > self.expiry


# class PasswordResetOTP(db.Model):
#     __tablename__ = "password_reset_otps"

#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # NEW
#     otp = db.Column(db.String(6), nullable=False)
#     purpose = db.Column(db.String(50), default="password_reset")  # NEW
#     expires_at = db.Column(db.DateTime, nullable=False)  # renamed from expiry
#     is_verified = db.Column(db.Boolean, default=False)
#     request_count = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user = db.relationship("User", backref="otps")  # NEW relationship

#     def is_expired(self):
#         return datetime.utcnow() > self.expires_at


# # ---- COMMUNITY ----
# class Era(db.Model):
#     __tablename__ = "eras"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), unique=True, nullable=False)
#     year_range = db.Column(db.String(50))  # e.g. "1950s-1980s"
#     image = db.Column(db.String(255))
#     description = db.Column(db.Text)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # relationships
#     zones = db.relationship("Zone", backref="era", cascade="all, delete-orphan")
#     members = db.relationship(
#         "User",
#         secondary=user_era_membership,
#         back_populates="joined_eras",
#     )

# class Zone(db.Model):
#     __tablename__ = "zones"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), unique=True, nullable=False)
#     description = db.Column(db.String(255))

#     era_id = db.Column(db.Integer, db.ForeignKey("eras.id"), nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)


# class Post(db.Model):
#     __tablename__ = "posts"
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     media = db.Column(db.Text, nullable=True)
#     pinned = db.Column(db.Boolean, default=False)
#     hot_thread = db.Column(db.Boolean, default=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     zone_id = db.Column(db.Integer, db.ForeignKey("zones.id"), nullable=False)


# class Comment(db.Model):
#     __tablename__ = "comments"
#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.Text, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)


# class Like(db.Model):
#     __tablename__ = "likes"
#     id = db.Column(db.Integer, primary_key=True)
#     type = db.Column(db.String(20), default="post")  # "post" or "comment"
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
#     comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)


# # ---- FEEDBACK ----
# class Feedback(db.Model):
#     __tablename__ = "feedback"
#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.Text, nullable=False)
#     vote_type = db.Column(db.String(10), nullable=False)  # "upvote" or "downvote"
#     upvotes = db.Column(db.Integer, default=0)
#     downvotes = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=True)
#     parent = db.relationship("Feedback", remote_side=[id], backref="replies")


# # ---- EVENTS ----
# event_participants = db.Table(
#     "event_participants",
#     db.Column("event_id", db.Integer, db.ForeignKey("events.id")),
#     db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
# )

# class Event(db.Model):
#     __tablename__ = "events"
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     description = db.Column(db.Text)
#     start_date = db.Column(db.DateTime, nullable=False)
#     end_date = db.Column(db.DateTime, nullable=True)
#     event_date = db.Column(db.DateTime, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     rsvps = db.relationship("RSVP", backref="event", cascade="all, delete-orphan")

#     participants = db.relationship(
#         "User", secondary=event_participants, backref="joined_events"
#     )


# class RSVP(db.Model):
#     __tablename__ = "rsvps"
#     __table_args__ = (
#         db.UniqueConstraint("user_id", "event_id", name="unique_user_event_rsvp"),
#     )

#     id = db.Column(db.Integer, primary_key=True)
#     status = db.Column(db.String(20), nullable=False)  # going, interested, not_going
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

# # ---- GAMIFICATION ----
# class Badge(db.Model):
#     __tablename__ = "badges"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     description = db.Column(db.String(255))
#     icon = db.Column(db.String(255))  # optional: link to image


# class UserBadge(db.Model):
#     __tablename__ = "user_badges"
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
#     badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"))


# class Mission(db.Model):
#     __tablename__ = "missions"
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     description = db.Column(db.Text)
#     points = db.Column(db.Integer, default=0)
#     start_date = db.Column(db.DateTime, default=datetime.utcnow)
#     end_date = db.Column(db.DateTime, nullable=True)

#     # Link mission to a badge (optional, some missions may not give badges)
#     badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), nullable=True)
#     badge = db.relationship("Badge", backref="missions")

#     # Track participants
#     participants = db.relationship("MissionParticipant", back_populates="mission")

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# class Idea(db.Model):
#     __tablename__ = "ideas"
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255), nullable=False)
#     content = db.Column(db.Text, nullable=False)
#     status = db.Column(db.String(20), default="submitted")  # submitted, validated, rejected
#     validated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
#     points_awarded = db.Column(db.Integer, default=0)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

#     # Rel for mentoring/moderation
#     mentor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


# class MissionParticipant(db.Model):
#     __tablename__ = "mission_participants"

#     id = db.Column(db.Integer, primary_key=True)
#     mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     status = db.Column(db.String(50), default="joined")  # joined | completed
#     joined_at = db.Column(db.DateTime, default=datetime.utcnow)
#     completed_at = db.Column(db.DateTime, nullable=True)

#     mission = db.relationship("Mission", back_populates="participants")
#     user = db.relationship("User", back_populates="missions")


# class FeedbackVote(db.Model):
#     __tablename__ = "feedback_votes"

#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
#     vote_type = db.Column(db.String(10), nullable=False)  # "upvote" or "downvote"
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     # relationships (optional but useful)
#     user = db.relationship("User", backref="feedback_votes", lazy=True)
#     feedback = db.relationship("Feedback", backref="votes", lazy=True)

#     def __repr__(self):
#         return f"<FeedbackVote {self.vote_type} by User {self.user_id} on Feedback {self.feedback_id}>"


# class Poll(db.Model):
#     __tablename__ = "polls"
#     id = db.Column(db.Integer, primary_key=True)
#     question = db.Column(db.String(255), nullable=False)
#     post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

#     options = db.relationship(
#         "PollOption", backref="poll", cascade="all, delete-orphan"
#     )
#     votes = db.relationship(
#         "PollVote", backref="direct_votes", cascade="all, delete-orphan"
#     )  # Keep as-is


# class PollOption(db.Model):
#     __tablename__ = "poll_options"
#     id = db.Column(db.Integer, primary_key=True)
#     text = db.Column(db.String(255), nullable=False)
#     votes_count = db.Column(db.Integer, default=0)
#     poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)


# class PollVote(db.Model):
#     __tablename__ = "poll_votes"
#     id = db.Column(db.Integer, primary_key=True)
#     option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
#     poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     __table_args__ = (
#         db.UniqueConstraint("user_id", "poll_id", name="unique_user_poll_vote"),
#     )

#     user = db.relationship("User", backref="poll_votes", lazy=True)
#     poll = db.relationship("Poll", backref="direct_votes", lazy=True)
#     option = db.relationship("PollOption", backref="votes", lazy=True)

#     def __repr__(self):
#         return f"<PollVote user_id={self.user_id} poll_id={self.poll_id} option_id={self.option_id}>"
