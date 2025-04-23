import os
import random
import time

import requests
from bs4 import BeautifulSoup

base_url = "https://dashboard.gooood.cn/api/wp/v2/fetch-posts?page=<page>&per_page=18&post_type%5B0%5D=post&post_type%5B1%5D=jobs"
from config import *

pages_folder = "./results/gooood/pages"
os.makedirs(pages_folder, exist_ok=True)
page = 1
while True:

    try:
        # Send a GET request to the website
        url = base_url.replace("<page>", str(page))
        print(f"Fetching page {page}, url = {url}")
        response = requests.get(url, headers=user_settings.headers)
        response.raise_for_status()  # Raise an error for bad status codes
        data = json.loads(response.text)
        if len(data) == 0:
            print("reached end")
            break
        with open(os.path.join(pages_folder, f"page_{str(page).zfill(5)}.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the website: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    page += 1
    time.sleep(random.random() * 0.2)