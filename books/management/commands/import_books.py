import os
import requests
from datetime import datetime

from django.core.management.base import BaseCommand
from books.models import Book, Author, Household

from PIL import Image
# from pyzbar.pyzbar import decode
# import zxingcpp
# import numpy as np
import easyocr
import re

from books.services import FetchBook


class Command(BaseCommand):
    help = "Scan barcode images and import books into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder_path",
            type=str,
            help="Path to folder containing barcode images",
        )

    def handle(self, *args, **kwargs):
        folder_path = kwargs["folder_path"]
        print(folder_path)
        household, _ = Household.objects.get_or_create(name='Sahityika Family')
        if not os.path.isdir(folder_path):
            self.stderr.write("❌ Invalid folder path")
            return

        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        self.stdout.write(f"📂 Found {len(images)} images")
        isbn_list = [
            "9780857197689",
            "9781847941831",
            "9780385550369",
            "9780571365425",
            "9780807014295",
            "9781401971366",
            "9781546171461",
            "9788126042456",
            "9788184803730",
            "9788126002962",
            "9788172290480",
            "9788194879008",
            "9788198394606",
            "9788119174331",
            "9789383814893"
        ]
        for isbn in isbn_list:
            # image_path = os.path.join(folder_path, image_name)

            try:
                # isbn = "9789392613234"
                if not isbn:
                    # self.stderr.write(f"⚠️ No barcode found: {image_name}")
                    continue

                # if Book.objects.filter(isbn=isbn).exists():
                #     self.stdout.write(f"⏭️ Already exists: {isbn}")
                #     continue

                book_data = FetchBook(isbn).fetch_book_data()
                if not book_data:
                    self.stderr.write(f"❌ No data for ISBN: {isbn}")
                    continue
                book_data["household"] = household
                # Book.objects.create(**book_data)
                book = Book.create_or_update_book(book_data)
                self.stdout.write(f"✅ Added: {book_data['title']}")

            except Exception as e:
                self.stderr.write(f"🔥 Error processing {isbn}: {e}")

        self.stdout.write("🎉 Import completed")

    def extract_isbn(self, image_path):
        image = Image.open(image_path)
        # barcodes = decode(image)
        #
        # for barcode in barcodes:
        #     # print(barcode)
        #     return barcode.data.decode("utf-8")
        
        # 2️⃣ OCR fallback
        # img_np = np.array(image)
        # results = zxingcpp.read_barcodes(img_np)
        # if results:
        #     return results[0].text

        reader = easyocr.Reader(['en'])
        results = reader.readtext(image_path)

        isbn = None

        for (_, text, confidence) in results:
            clean = text.replace("-", "").replace(" ", "").upper()

            if re.fullmatch(r'97[89]\d{10}', clean):
                isbn = clean
                break

            if re.fullmatch(r'\d{9}[\dX]', clean):
                isbn = clean
                break

        return None


    