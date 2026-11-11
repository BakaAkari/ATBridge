"""Set the real Chrome Web Store ID only after the listing exists."""
import re

CHROME_STORE_ID = ''


def store_url():
    if not re.fullmatch(r'[a-p]{32}', CHROME_STORE_ID):
        return None
    return 'https://chromewebstore.google.com/detail/' + CHROME_STORE_ID
