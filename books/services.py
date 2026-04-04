import requests
from datetime import datetime

class FetchBook:
    URL = "https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"

    def __init__(self, isbn):
        self.isbn = isbn

    def fetch_book_data(self):
        url = self.URL.format(isbn=self.isbn)
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        items = data.get("items")

        if not items:
            return None

        info = items[0]["volumeInfo"]

        # Extract ISBNs
        isbn_10 = ""
        isbn_13 = ""

        for item in info.get("industryIdentifiers", []):
            if item["type"] == "ISBN_10":
                isbn_10 = item["identifier"]
            elif item["type"] == "ISBN_13":
                isbn_13 = item["identifier"]
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
            "published_date": self.parse_date(info.get("publishedDate")),
            "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
            "preview_link": info.get("previewLink", ""),
            "info_link": info.get("infoLink", ""),
        }

    def parse_date(self, date_str):
        """
        Google Books can return:
        - YYYY
        - YYYY-MM
        - YYYY-MM-DD
        """
        if not date_str:
            return None

        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None