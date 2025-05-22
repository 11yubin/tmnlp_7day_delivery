from dotenv import load_dotenv
import os
import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
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

    print(f"수집된 링크 개수: {len(links)}")
    # 저장
    news_links = pd.DataFrame({'id': range(len(links)), 'link': links})

    driver.quit()

    news_links.to_csv('links.csv')
    print("✅ get links")

# 더보기 스크롤 -> 댓글 전부 수집하기 위함
def click_all_more_buttons(driver, max_clicks=30):
    click_count = 0
    while click_count < max_clicks:
        try:
            time.sleep(15)

            driver.find_element(By.XPATH, '//*[@id="cbox_module"]/div[2]/div[9]/a').click()
            # if more_button.is_displayed():
            #     driver.execute_script("arguments[0].click();", more_button)
            #     time.sleep(1.5)
            #     click_count += 1
            # else:
            #     break
        except NoSuchElementException:
            # 더보기 버튼 없음: 종료
            break
        except Exception as e:
            # 이외의 오류 발생
            print(e)
            break

def get_news_info():
    links = pd.read_csv('./links.csv')
    link = links['link'][12]
    title, content, press, date, comments_link = None, None, None, None, None

    # 댓글 수집 -> js라 soup는 안됨
    driver.get(link)
    time.sleep(1.5)

    # 댓글 iframe으로 전환 (모바일은 iframe 없음 / PC는 존재)
    try:
        driver.switch_to.frame("commentFrame")
    except:
        pass

    # 댓글 개수 텍스트 가져오기
    try:
        comments_count = driver.find_element(By.ID, "comment_count")
        count = int(comments_count.text)
        print("댓글 수:", count)

        if int(count) >= 1:
            comments = []
            comments_link = comments_count.get_attribute('href')

            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            print(comments_link)

            res = requests.get(link, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")

            # 제목
            title = soup.select_one("h2.media_end_head_headline").text.strip()

            # 본문
            content = soup.select_one("article#dic_area").text.strip()
            
            # 언론사
            press_tag = soup.select_one("img.media_end_head_top_logo_img")
            press = press_tag["title"].strip() if press_tag else None

            # 날짜
            date_tag = soup.select_one("span.media_end_head_info_datestamp_time")
            date_str = date_tag["data-date-time"] if date_tag else None
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else None

            # 댓글 수집 -> 수정중
            driver.get(comments_link)
            comments_list = driver.find_elements(By.CSS_SELECTOR, ".u_cbox_contents")

            # 확인 출력
            print("제목:", title)
            print("언론사:", press)
            print("작성일:", date)
            print("본문:\n", content)
            print(len(comments_list))

            for c in range (len(comments_list)):
                comment = comments_list[c].text
                like = driver.find_element(By.XPATH, f'//*[@id="cbox_module_wai_u_cbox_content_wrap_tabpanel"]/ul/li[{c+1}]/div[1]/div/div[4]/div/a[1]/em').text
                print(comment, like)

                comments.append([comment, like])


    except Exception as e:
        print("댓글 수 없음")
        print(e)
    
if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    get_news_info()

    driver.quit()