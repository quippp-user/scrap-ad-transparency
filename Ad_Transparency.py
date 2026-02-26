from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
import os
import csv
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


# Chrome options
options = Options()
options.add_argument("--log-level=3")
options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.add_argument("--start-maximized")

# IMPORTANT: No chromedriver path needed on Mac
driver = webdriver.Chrome(options=options)

#store images link
Images_URL = "Images_URL.csv"

# Base URL
base_url = "https://adstransparency.google.com/?region=GB&start-date=2025-01-01&end-date=2026-02-25&platform=SEARCH&domain=clearabee.co.uk&format=TEXT"
OUTPUT_FOLDER = "/Users/faiyaz/Code/quippp/app-image-ocr/src/clear/images"
driver.get(base_url)

# Random initial wait
time.sleep(random.randint(6, 10))

# Scroll to bottom loop (improved for dynamic loading)
scroll_pause_time = 6
last_height = driver.execute_script("return document.body.scrollHeight")

while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(scroll_pause_time + random.random()*2)

    # Wait for ads to load
    driver.execute_script("window.scrollBy(0, -300);")
    time.sleep(2)

    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# Wait a bit more for final lazy loads
time.sleep(5)

# Parse page
html = driver.page_source
soup = BeautifulSoup(html, 'html5lib')

# Extract image URLs
img_tags = soup.find_all("img")
filtered_img_urls = [
    img['src'] for img in img_tags
    if img.get('src') and "/archive/simgad/" in img['src']
]

# Extract categories/links
links = driver.find_elements(By.XPATH, "//a[contains(@href,'advertiser') or contains(@href,'ad/')]")
categories = [link.get_attribute("href") for link in links]

# Equalize lengths
max_len = max(len(filtered_img_urls), len(categories))
filtered_img_urls += [""] * (max_len - len(filtered_img_urls))
categories += [""] * (max_len - len(categories))

# Save to CSV
df = pd.DataFrame({
    "Image_URLs": filtered_img_urls,
    "Categories": categories
})

df.to_csv(Images_URL, index=False)
driver.quit()
print("Images saved")



CSV_FILE = Images_URL

MAX_THREADS = 30            
TIMEOUT = 15
RETRIES = 3

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_filename_from_url(url, index):
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)

    if not name or "." not in name:
        name = f"image_{index}.jpg"

    return name


def download_image(args):
    index, url = args
    filename = get_filename_from_url(url, index)
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    if os.path.exists(filepath):
        return

    for attempt in range(RETRIES):
        try:
            response = requests.get(url, timeout=TIMEOUT, stream=True)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return
        except Exception:
            time.sleep(1)

    print(f"Failed: {url}")


def main():
    urls = []

    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            urls.append((i, row["Image_URLs"].strip()))

    print(f"Found {len(urls)} images. Starting download...\n")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        list(tqdm(executor.map(download_image, urls), total=len(urls)))

    print("\nDone!")


if __name__ == "__main__":
    main()
