MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 12

# Common/easily-guessed passwords rejected regardless of length. Mirrored
# exactly in the frontend (src/utils/passwordValidation.js) so both sides
# agree on what's rejected — a password rejected by one and accepted by the
# other would be a confusing inconsistency for the user.
WEAK_PASSWORDS = {
    "password",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty",
    "qwerty123",
    "admin",
    "azerty",
    "letmein",
    "00000000",
    "11111111",
    "123123123",
    "iloveyou",
    "welcome",
    "monkey",
    "football",
    "abc12345",
    "abcd1234",
    "passw0rd",
}


def validate_password_strength(password: str) -> str | None:
    """Returns an error message if the password is rejected, or None if it's
    acceptable. Kept as a plain function (rather than a Pydantic validator) so
    the exact same rules and wording can be reused by both signup and
    reset-password without duplicating the checks."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters"

    if password.lower() in WEAK_PASSWORDS:
        return "This password is too common, please choose a stronger one"

    return None
