import requests
import time
import os
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 目标 URL
ARCHDAILY_SEARCH_URL = "https://www.archdaily.com/search/projects?p="

# 伪造 User-Agent
ua = UserAgent()
HEADERS = {"User-Agent": ua.random}

# 图片存储目录
IMG_FOLDER = "archdaily_images"
os.makedirs(IMG_FOLDER, exist_ok=True)


def get_project_links():
    """获取 ArchDaily 上的 3 个建筑项目链接"""
    url = ARCHDAILY_SEARCH_URL + "1"  # 只爬取第 1 页
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print("❌ 无法访问 ArchDaily")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    project_elements = soup.find_all("div", class_="afd-search-list__item")
    project_links = ["https://www.archdaily.com" + item.find("a")["href"] for item in project_elements if item.find("a")]

    return project_links[:3]  # 取前 3 个项目


def scrape_project_details(project_url):
    """爬取建筑项目的详情和图片"""
    response = requests.get(project_url, headers=HEADERS)

    if response.status_code != 200:
        print(f"❌ 请求失败: {project_url}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # 获取建筑信息
    title = soup.find("h1", class_="afd-title-big").text.strip() if soup.find("h1", class_="afd-title-big") else "未知"
    architect = soup.find("strong", class_="afd-project-lead__link").text.strip() if soup.find("strong", class_="afd-project-lead__link") else "未知"
    description = " ".join([p.text.strip() for p in soup.find_all("p")])[:500]  # 取前 500 个字符

    print(f"📌 项目: {title}")
    print(f"🏗 建筑师: {architect}")
    print(f"📖 简介: {description[:100]}...")

    # 获取图片链接
    img_tags = soup.find_all("img", class_="picture--content__img")
    img_urls = [img["src"] for img in img_tags if "src" in img.attrs]

    for img_url in img_urls:
        download_image(img_url, title)

    return {"title": title, "architect": architect, "description": description, "url": project_url, "images": img_urls}


def download_image(img_url, title):
    """下载建筑图片"""
    try:
        response = requests.get(img_url, headers=HEADERS, stream=True)
        if response.status_code == 200:
            filename = f"{IMG_FOLDER}/{title.replace(' ', '_')}.jpg"
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"✅ 下载图片: {filename}")
    except Exception as e:
        print(f"❌ 图片下载失败: {e}")


def main():
    """爬取 3 个建筑项目"""
    project_links = get_project_links()

    for project_url in project_links:
        scrape_project_details(project_url)
        time.sleep(2)  # 避免被封


if __name__ == "__main__":
    main()
