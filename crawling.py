from dotenv import load_dotenv
import os
import psycopg2
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def db_connect():
    load_dotenv()

    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        print("✅ 연결 성공")
    except Exception as e:
        print("❌ 연결 실패:", e)

def crawling():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    query = "7일 배송"
    url = f"https://search.naver.com/search.naver?ssc=tab.news.all&query={query}&sm=tab_opt&sort=0&photo=0&field=0&pd=-1&ds=2025.05.21&de=2025.05.21&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=&is_sug_officeid=0&office_category=&service_area=1"
    driver.get(url)
    print("✅ driver open")

    # for _ in range(20):
    #     driver.execute_script("window.scrollBy(0, 1500);")
    #     time.sleep(1)

    # 끝까지 스크롤
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)  # 로딩 시간 여유

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

        time.sleep(1)
    
    print("✅ scroll complete")
    
    # time.sleep(100)

    links = []

    for i in range(1, 77):  # div[1] ~ div[15]
        for j in range(1, 10):
            try:
                if i==1:
                    xpath = f'/html/body/div[3]/div[2]/div[1]/div[1]/section/div[1]/div[2]/ul/div/div/div/div/div[{j}]/div[1]/div[1]/div[2]/span[4]/a'
                else:
                    xpath = f'/html/body/div[3]/div[2]/div[1]/div[1]/section/div[1]/div[2]/ul/div[{i}]/div/div/div/div[{j}]/div[1]/div[1]/div[2]/span[4]/a'
                
                element = driver.find_element(By.XPATH, xpath)
                href = element.get_attribute("href")
                links.append(href)

            except Exception as e:
                continue
        
            print(f"{i} page 완료, 총 {len(links)}")


    # link_elements = driver.find_elements(By.CSS_SELECTOR, "a.news_tit")
    # links = [elem.get_attribute("href") for elem in link_elements]

    print(f"🔗 수집된 링크 개수: {len(links)}")
    # 저장
    news_links = pd.DataFrame({'id': range(len(links)), 'link': links})

    driver.quit()

    news_links.to_csv('links.csv')
    print("✅ get links")

def main():
    links = pd.read_csv('./links.csv')
    link = links['link'][0]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(link, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 제목
    title = soup.select_one("h2.media_end_head_headline").text.strip()

    # 본문
    content = soup.select_one("article#dic_area").text.strip()

    # 기자명 (없을 수 있음)
    writer_tag = soup.select_one("em.media_end_head_journalist_name")
    writer = writer_tag.text.strip() if writer_tag else None

    # 언론사 (img alt나 title 속성)
    press_tag = soup.select_one("img.media_end_head_top_logo_img")
    press = press_tag["title"].strip() if press_tag else None

    # 작성일 (시간)
    date_tag = soup.select_one("span.media_end_head_info_datestamp_time")
    date_str = date_tag["data-date-time"] if date_tag else None
    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else None

    # 확인 출력
    print("📰 제목:", title)
    print("📝 기자:", writer)
    print("🏢 언론사:", press)
    print("📅 작성일:", date)
    print("📄 본문:\n", content)

    

if __name__ == "__main__":
    main()