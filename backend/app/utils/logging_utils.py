def safe_log(message: str) -> None:
    """Prints to console without crashing on Windows' cp1252 codepage when the
    message contains characters (e.g. from LLM output or external APIs) that
    aren't representable in it."""
    print(message.encode("ascii", errors="replace").decode("ascii"))
