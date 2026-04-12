import logging
import requests
from datetime import datetime


from django.conf import settings

logger = logging.getLogger(__name__)


def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


class GoogleBooksSource:
    NAME = "Google Books"
    URL = "https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"

    def fetch(self, isbn):
        logger.warning("[%s] Searching for ISBN: %s", self.NAME, isbn)
        # Try ISBN-13 first, then fall back to ISBN-10 if available
        isbns_to_try = [isbn]
        if len(isbn) == 13 and isbn.startswith("978"):
            # Derive ISBN-10 from ISBN-13 as fallback
            isbn10_body = isbn[3:12]
            check = sum((10 - i) * int(d) for i, d in enumerate(isbn10_body)) % 11
            check_char = "X" if check == 0 else str((11 - check) % 11)
            isbns_to_try.append(isbn10_body + check_char)

        try:
            for candidate in isbns_to_try:
                url = self.URL.format(isbn=candidate)
                if settings.USE_GOOGLE_KEY:
                    url += f"&key={settings.GOOGLE_BOOKS_API_KEY}"
                print(url)
                response = requests.get(
                    url,
                    timeout=10
                )
                if response.status_code != 200:
                    logger.warning("[%s] HTTP %s for ISBN: %s", self.NAME, response.status_code, candidate)
                    continue
                items = response.json().get("items")
                if items:
                    break
            else:
                logger.warning("[%s] No results found for ISBN: %s", self.NAME, isbn)
                return None
            info = items[0]["volumeInfo"]
            isbn_10, isbn_13 = "", ""
            for item in info.get("industryIdentifiers", []):
                if item["type"] == "ISBN_10":
                    isbn_10 = item["identifier"]
                elif item["type"] == "ISBN_13":
                    isbn_13 = item["identifier"]
            logger.warning("[%s] Found '%s' for ISBN: %s", self.NAME, info.get("title"), isbn)
            return {
                "title": info.get("title", "Unknown"),
                "subtitle": info.get("subtitle", ""),
                "authors": info.get("authors", []),
                "isbn_10": isbn_10,
                "isbn_13": isbn_13,
                "categories": ", ".join(info.get("categories", [])),
                "description": info.get("description", ""),
                "page_count": info.get("pageCount"),
                "language": info.get("language", ""),
                "publisher": info.get("publisher", ""),
                "published_date": parse_date(info.get("publishedDate")),
                "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
                "preview_link": info.get("previewLink", ""),
                "info_link": info.get("infoLink", ""),
            }
        except requests.RequestException as e:
            logger.error("[%s] Request failed for ISBN %s: %s", self.NAME, isbn, e)
            return None


class OpenLibrarySource:
    NAME = "Open Library"
    # Search API has much better coverage than /api/books
    URL = "https://openlibrary.org/search.json?isbn={isbn}&limit=1"

    def fetch(self, isbn):
        logger.warning("[%s] Searching for ISBN: %s", self.NAME, isbn)
        try:
            response = requests.get(self.URL.format(isbn=isbn), timeout=10)
            if response.status_code != 200:
                logger.warning("[%s] HTTP %s for ISBN: %s", self.NAME, response.status_code, isbn)
                return None
            data = response.json()
            docs = data.get("docs", [])
            if not docs:
                logger.warning("[%s] No results found for ISBN: %s", self.NAME, isbn)
                return None
            info = docs[0]

            authors = info.get("author_name", [])

            isbn_list = info.get("isbn", [])
            isbn_10 = next((i for i in isbn_list if len(i) == 10), "")
            isbn_13 = next((i for i in isbn_list if len(i) == 13), isbn)

            subjects = ", ".join(info.get("subject", [])[:5])

            cover_id = info.get("cover_i")
            thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""

            publisher_list = info.get("publisher", [])
            publisher = publisher_list[0] if publisher_list else ""

            publish_year = str(info.get("first_publish_year", ""))

            logger.warning("[%s] Found '%s' for ISBN: %s", self.NAME, info.get("title"), isbn)
            return {
                "title": info.get("title", "Unknown"),
                "subtitle": info.get("subtitle", ""),
                "authors": authors,
                "isbn_10": isbn_10,
                "isbn_13": isbn_13,
                "categories": subjects,
                "description": "",
                "page_count": info.get("number_of_pages_median"),
                "language": info.get("language", [""])[0] if info.get("language") else "",
                "publisher": publisher,
                "published_date": parse_date(publish_year),
                "thumbnail": thumbnail,
                "preview_link": "",
                "info_link": f"https://openlibrary.org{info.get('key', '')}",
            }
        except requests.RequestException as e:
            logger.error("[%s] Request failed for ISBN %s: %s", self.NAME, isbn, e)
            return None


class LibraryOfCongressSource:
    NAME = "Library of Congress"
    URL = "https://www.loc.gov/search/?q={isbn}&fo=json&at=results"

    def fetch(self, isbn):
        logger.warning("[%s] Searching for ISBN: %s", self.NAME, isbn)
        try:
            response = requests.get(self.URL.format(isbn=isbn), timeout=10)
            if response.status_code != 200:
                logger.warning("[%s] HTTP %s for ISBN: %s", self.NAME, response.status_code, isbn)
                return None
            results = response.json().get("results", [])
            if not results:
                logger.warning("[%s] No results found for ISBN: %s", self.NAME, isbn)
                return None
            info = results[0]

            title = info.get("title", "Unknown")
            if not title or title == "Unknown":
                logger.warning("[%s] No results found for ISBN: %s", self.NAME, isbn)
                return None

            contributors = info.get("contributor", []) or info.get("creator", [])
            authors = [c.strip().rstrip(",") for c in contributors]

            isbn_13 = isbn if len(isbn) == 13 else ""
            isbn_10 = isbn if len(isbn) == 10 else ""

            subjects = ", ".join(info.get("subject", [])[:5])
            date_str = info.get("date", "")
            publisher_info = info.get("publisher", [])
            publisher = publisher_info[0] if publisher_info else ""

            logger.warning("[%s] Found '%s' for ISBN: %s", self.NAME, title, isbn)
            return {
                "title": title,
                "subtitle": "",
                "authors": authors,
                "isbn_10": isbn_10,
                "isbn_13": isbn_13,
                "categories": subjects,
                "description": info.get("description", ""),
                "page_count": None,
                "language": info.get("language", [""])[0] if info.get("language") else "",
                "publisher": publisher,
                "published_date": parse_date(date_str),
                "thumbnail": info.get("image_url", [""])[0] if info.get("image_url") else "",
                "preview_link": info.get("url", ""),
                "info_link": info.get("id", ""),
            }
        except requests.RequestException as e:
            logger.error("[%s] Request failed for ISBN %s: %s", self.NAME, isbn, e)
            return None


class OpenLibraryDirectSource:
    """
    Hits the direct ISBN endpoint on Open Library (/isbn/{isbn}.json).
    This is a different index than the search API and sometimes has editions
    that the search API misses.
    """
    NAME = "Open Library (direct)"
    URL = "https://openlibrary.org/isbn/{isbn}.json"

    def fetch(self, isbn):
        logger.warning("[%s] Searching for ISBN: %s", self.NAME, isbn)
        try:
            response = requests.get(self.URL.format(isbn=isbn), timeout=10, allow_redirects=True)
            if response.status_code != 200:
                logger.warning("[%s] HTTP %s for ISBN: %s", self.NAME, response.status_code, isbn)
                return None

            info = response.json()
            title = info.get("title", "")
            if not title:
                logger.warning("[%s] No results found for ISBN: %s", self.NAME, isbn)
                return None

            # Resolve authors (they are references like /authors/OL123A.json)
            authors = []
            for author_ref in info.get("authors", []):
                key = author_ref.get("key", "")
                if key:
                    try:
                        author_resp = requests.get(f"https://openlibrary.org{key}.json", timeout=5)
                        if author_resp.status_code == 200:
                            authors.append(author_resp.json().get("name", ""))
                    except requests.RequestException:
                        pass

            isbn_list = info.get("isbn_13", []) + info.get("isbn_10", [])
            isbn_13 = next((i for i in info.get("isbn_13", []) if len(i) == 13), isbn if len(isbn) == 13 else "")
            isbn_10 = next((i for i in info.get("isbn_10", []) if len(i) == 10), isbn if len(isbn) == 10 else "")

            cover_id = info.get("covers", [None])[0]
            thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""

            publishers = info.get("publishers", [])
            publisher = publishers[0] if publishers else ""

            publish_date = info.get("publish_date", "")

            logger.warning("[%s] Found '%s' for ISBN: %s", self.NAME, title, isbn)
            return {
                "title": title,
                "subtitle": info.get("subtitle", ""),
                "authors": [a for a in authors if a],
                "isbn_10": isbn_10,
                "isbn_13": isbn_13,
                "categories": "",
                "description": "",
                "page_count": info.get("number_of_pages"),
                "language": "",
                "publisher": publisher,
                "published_date": parse_date(publish_date),
                "thumbnail": thumbnail,
                "preview_link": "",
                "info_link": f"https://openlibrary.org{info.get('key', '')}",
            }
        except requests.RequestException as e:
            logger.error("[%s] Request failed for ISBN %s: %s", self.NAME, isbn, e)
            return None


class FetchBook:
    SOURCES = [
        GoogleBooksSource(),
        OpenLibrarySource(),
        OpenLibraryDirectSource(),
        LibraryOfCongressSource(),
    ]

    def __init__(self, isbn):
        self.isbn = isbn

    def fetch_book_data(self):
        logger.warning("Starting book lookup for ISBN: %s", self.isbn)
        for source in self.SOURCES:
            result = source.fetch(self.isbn)
            if result and result.get("title") and result["title"] != "Unknown":
                logger.warning("Book found via %s for ISBN: %s", source.NAME, self.isbn)
                return result
        logger.warning("Book not found in any source for ISBN: %s", self.isbn)
        return None
