from urllib.parse import urlparse


def parse_subscription_token(text: str) -> str:
    """Extract a PasarGuard subscription token from a URL or /start payload."""
    text = text.strip()
    if text.startswith("/start "):
        text = text.split(maxsplit=1)[1].strip()

    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if "sub" in parts:
            sub_index = parts.index("sub")
            if len(parts) > sub_index + 1:
                return parts[sub_index + 1]
        if parts:
            return parts[-1]

    return text.strip("/").split("/")[-1]
