from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    # False for a fresh password-based signup until the confirmation link is
    # clicked (see verification_token below); True immediately for Google
    # sign-ins (Google already verified the email — see auth_router.py's
    # login_with_google) and for every account that existed before this
    # feature shipped (backfilled at migration time in main.py, never
    # retroactively locked out).
    email_verified = Column(Boolean, nullable=False, default=False)

    verification_token = Column(String, unique=True, nullable=True)

    verification_token_expires_at = Column(String, nullable=True)

    # Nullable: a Google-only account (no password ever set) has no hash.
    # Password-based accounts are unaffected — this column stays required in
    # spirit for them, just no longer enforced at the DB level so a Google
    # signup can leave it empty instead of needing a fake placeholder hash.
    password_hash = Column(String, nullable=True)

    # Google's stable per-account identifier ("sub" claim in the verified ID
    # token) — set on first Google sign-in, either for a brand-new account or
    # linked onto an existing email/password account that shares the same
    # (Google-verified) email. None for accounts that have never used Google.
    google_id = Column(String, unique=True, nullable=True)

    created_at = Column(String, nullable=True)

    reset_token = Column(String, unique=True, nullable=True)

    reset_token_expires_at = Column(String, nullable=True)

    workspace_memberships = relationship(
        "WorkspaceMember",
        back_populates="user"
    )

    review_comments = relationship(
        "ReviewComment",
        back_populates="user"
    )