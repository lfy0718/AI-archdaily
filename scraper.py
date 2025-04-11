import os
import json
import time
import requests
from bs4 import BeautifulSoup

# ArchDaily 搜索结果 URL
ARCHDAILY_SEARCH_URL = "https://www.archdaily.com/search/projects?adkq=building&page="

# 请求头，避免反爬
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# 图片保存目录
IMG_FOLDER = "archdaily_images"
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

# 项目数据存储文件
DATA_FILE = "projects.json"


def get_project_links(page=1):
    """ 获取搜索结果页面的项目链接 """
    url = ARCHDAILY_SEARCH_URL + str(page)
    print(f"🔍 爬取搜索页: {url}")

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print("❌ 无法访问 ArchDaily，状态码:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    project_elements = soup.find_all("div", class_="afd-search-list__item")

    if not project_elements:
        print("⚠️ 未找到项目元素，可能是网页结构改变或被反爬！")
        return []

    project_links = ["https://www.archdaily.com" + item.find("a")["href"] for item in project_elements if
                     item.find("a")]
    print(f"✅ 找到 {len(project_links)} 个项目")

    return project_links[:5]  # 仅获取前 5 个


def scrape_project_details(project_url):
    """ 获取项目详情，包括标题、介绍和图片 """
    print(f"📡 爬取项目页面: {project_url}")

    response = requests.get(project_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ 请求失败: {project_url}，状态码: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # 获取项目标题
    title_tag = soup.find("h1", class_="afd-title-big")
    title = title_tag.text.strip() if title_tag else "未知项目"

    # 获取项目介绍
    description_tag = soup.find("div", class_="afd-paragraph-big")
    description = description_tag.text.strip() if description_tag else "暂无介绍"

    # 获取所有图片
    img_tags = soup.find_all("img", class_="picture--content__img")
    img_urls = [img["src"] for img in img_tags if "src" in img.attrs]

    # 下载图片
    saved_images = []
    for img_url in img_urls[:3]:  # 仅下载前 3 张图片，避免过多
        img_path = download_image(img_url, title)
        if img_path:
            saved_images.append(img_path)

    return {
        "title": title,
        "description": description,
        "images": saved_images,
        "url": project_url
    }


def download_image(img_url, title):
    """ 下载图片并保存 """
    print(f"🌍 下载图片: {img_url}")

    try:
        response = requests.get(img_url, headers=HEADERS, stream=True)
        if response.status_code == 200:
            filename = f"{IMG_FOLDER}/{title.replace(' ', '_')}.jpg"
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"✅ 图片下载成功: {filename}")
            return filename
        else:
            print(f"❌ 图片下载失败: {img_url}")
    except Exception as e:
        print(f"⚠️ 图片下载出错: {e}")
    return None


def save_data(data):
    """ 保存数据到 JSON 文件 """
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print(f"💾 数据保存成功: {DATA_FILE}")


def main():
    """ 爬取 ArchDaily 项目数据 """
    print("🚀 开始爬取 ArchDaily 项目数据...")

    project_links = get_project_links()
    if not project_links:
        print("⚠️ 没有找到任何项目，程序退出")
        return

    all_projects = []
    for project_url in project_links:
        project_data = scrape_project_details(project_url)
        if project_data:
            all_projects.append(project_data)

        time.sleep(2)  # 避免请求过快被封

    # 保存数据
    save_data(all_projects)
    print("🎉 爬取完成！")


if __name__ == "__main__":
    main()
