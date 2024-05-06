import re
import os
import ast
import time
import json
import pymysql
import logging
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, ElementNotInteractableException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.support import expected_conditions as EC

import textwrap
# Used to securely store your API key
import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from openai import OpenAI

load_dotenv()

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--disable-blink-features=AutomationControlled')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# # all IT jobs
# driver.get("https://hk.jobsdb.com/jobs?classification=6281")

# # all gov jobs
# driver.get("https://hk.jobsdb.com/jobs?classification=1210")

# crawl job_ids of each page
def crawl_job_codes():
    all_job_codes = []

    driver.get("https://hk.jobsdb.com/jobs?classification=6281")

    # for page_number in range(20,21):
    #     driver.get(f"https://hk.jobsdb.com/jobs-in-information-communication-technology?page={page_number}")
    try:
        posts = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, \
            "article.y735df0, article.y735df1, article._1iz8dgs7i, article._1iz8dgs6e, article._1iz8dgs9q, \
            article._1iz8dgs8m, article._1iz8dgsh, article._1iz8dgs66, article._1iz8dgs5e, article.uo6mkg, \
            article.uo6mke, article.uo6mkf, article._94v4w18, article._94v4w1b, article._1iz8dgs32, \
            article._1iz8dgs35")))
        for post in posts:
            div = post.find_element(By.CSS_SELECTOR, "div.y735df0, div._1iz8dgs4y, div._1iz8dgs4w")
            a_tag = div.find_element(By.CSS_SELECTOR, "a[data-automation='job-list-view-job-link']")
            job_link= a_tag.get_attribute("href")
            if job_link:
                pattern = r'/job/(\d+)\?'
                matches = re.findall(pattern, job_link)
                if matches:
                    # Extract the first match
                    job_code = matches[0]
                    print(job_code)
                    all_job_codes.append(job_code)
            else:
                logging.error("No job link found for post: %s", post.text)
    except StaleElementReferenceException:
        # Retry if a stale element reference exception occurs
        logging.error("didn't get page job_ids")

    while True:
        try:
            next_button_a = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, \
                    'nav.y735df0.y735df1[aria-label="Pagination of results"] \
                    li.y735df0._1iz8dgsa6._1iz8dgs9v._1iz8dgsw \
                    a[title="Next"]')))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button_a)
            next_button_a.click()

            try:
                posts = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, \
                "article.y735df0, article.y735df1, article._1iz8dgs7i, article._1iz8dgs6e, article._1iz8dgs9q, \
                article._1iz8dgs8m, article._1iz8dgsh, article._1iz8dgs66, article._1iz8dgs5e, article.uo6mkg, \
                article.uo6mke, article.uo6mkf, article._94v4w18, article._94v4w1b, article._1iz8dgs32, \
                article._1iz8dgs35")))
            
                if not posts:
                    break

                for post in posts:
                    div = post.find_element(By.CSS_SELECTOR, "div.y735df0, div._1iz8dgs4y, div._1iz8dgs4w")
                    a_tag = div.find_element(By.CSS_SELECTOR, "a[data-automation='job-list-view-job-link']")
                    job_link = a_tag.get_attribute("href")
                    if job_link:
                        pattern = r'/job/(\d+)\?'
                        matches = re.findall(pattern, job_link)
                        if matches:
                            # Extract the first match
                            job_code = matches[0]
                            print(job_code)
                            all_job_codes.append(job_code)
                    else:
                        logging.error("No job link found for post: %s", post.text)
            except Exception as e:
                logging.error("An error occurred: %s", str(e))
                break
        except ElementClickInterceptedException:
            break        
        except (StaleElementReferenceException, TimeoutException) as e:
            logging.error(f"Error occurred: {e}")

    return all_job_codes

def get_gemini_summary(content): 

    empty_json = {'job_code': '', 'job_title': '', 'company_name': '', 'job_location': '', 'salary_period': '', \
                'min_salary': 0, 'max_salary': 0, 'edu_level': '', 'work_experience': '', 'skills': '', \
                'travel': '', 'management': '', 'remote': '', 'category':[], 'job_source': '', \
                'create_date':''}

    response_json = {'job_code': '8495k', 'job_title': 'Senior/Principal Data Scientist 資深資料科學家', 'company_name': '瑞健股份有限公司', 'job_location': '桃園市蘆竹區', 'salary_period': '待遇面議', \
                    'min_salary': 0, 'max_salary': 0, 'edu_level': '大學以上', 'work_experience': '5年以上', 'skills': 'Java,C++,C#,J2EE,Python', \
                    'travel': '無需出差外派', 'management': '不需負擔管理責任', 'remote': '不可遠端工作', 'category': ['軟體／工程類人員'], 'job_source': 'https://www.104.com.tw/job/8495k', \
                    'create_date': '2024-04-28 00:00:00'}
    
    category_list = ["軟體／工程類人員", "iOS工程師", "Android工程師", "前端工程師", "後端工程師", \
        "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", \
        "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", \
        "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", \
        "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", \
        "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", \
        "資料庫管理人員", "MIS／網管主管", "資安主管"]

    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()
    
    prompt = f"""
    一定要用繁體中文、接近104人力銀行的敘述風格，和包含16個條件的回答問題。
    一定要符合 = {empty_json}，curly brackets前不要有任何文字
    回傳範例格式 = {response_json}
    閱讀下面這個串列的job code和網頁工作敘述然後擷取我需要的內容，總共有很多筆資料

    {content}

    1.'job_title': 填寫工作職位名稱，可以是英文或中文
    2.'company_name'　保留原本語言
    3.'job_location'　在香港，要翻譯成香港的地名（例如：香港中環），中間不要空白
    4.'salary_period': 只能填寫：待遇面議（沒有資料），或是月薪多少HKD（例如：月薪13,000-16,000HKD，如果是年薪就換算成月薪）
    如果是annual pay，要轉換成月薪
    5.'min_salary': 只填寫數字，沒有的話不要寫，月薪最低的數字
    6.'max_salary': 只填寫數字，沒有的話不要寫，月薪最高的數字，如果只有一個數字那就和'min_salary'相同
    7.'edu_level'： 只能填寫：不拘、高中職、專科、大學、碩士、博士
    8.'work_experience'：只能填寫：不拘 或幾年以上（例如：1年以上、4年以上）
    9.'skills'：請填寫程式語言和軟體相關的技能，關鍵單字，最多不超2個詞，沒有的話回傳None
    10.'travel'：只能填寫：需出差外派　或　無需出差外派
    11.'management'：只能填寫：需負擔管理責任　或　不需負擔管理責任
    12.'remote'只能填寫：可遠端工作　或　不可遠端工作
    13.'category'：一定要填寫，只能從category_list裡面的分類選1-3個適合的，至少要有一個，一字不差
    14.'create_date'：填{tw_date}，一字不差
    15.'job_code'：填串列裡的'job_code'，一字不差
    16.'job_source'：填"https://hk.jobsdb.com/job/'job_code'"（例如："https://hk.jobsdb.com/job/75431589"），一字不差

    工作分類：["軟體／工程類人員", "iOS工程師", "Android工程師", "前端工程師", "後端工程師", 
        "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", 
        "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", 
        "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", 
        "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", 
        "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", 
        "資料庫管理人員", "MIS／網管主管", "資安主管"]

    category_list = {category_list}
    """
    
    response = model.generate_content(prompt)
    print(response)

    try:
        response = response.text
        print(response)
        # convert to dict
        dict_response = eval(response)
        print(type(dict_response))
        return dict_response
    except ValueError as e:
        logging.error("Error accessing response text:", e)

def get_openai_summary(content):
    
    list_form = "[[job_code, job_description],[job_code, job_description]]"
    empty_json = {'job_code': '8495k', 'job_title': '', 'company_name': '', 'job_location': '', 'salary_period': '', \
                'min_salary': 0, 'max_salary': 0, 'edu_level': '', 'work_experience': '', 'skills': None, 'travel': '', 
                'management': '', 'remote': '', 'category':[], 'job_source': '', 'create_date':''}

    example_json = {'job_code': '8495k', 'job_title': 'Senior/Principal Data Scientist 資深資料科學家', \
                    'company_name': '瑞健股份有限公司', 'job_location': '桃園市蘆竹區', 'salary_period': '待遇面議', \
                    'min_salary': 0, 'max_salary': 0, 'edu_level': '大學以上', 'work_experience': '5年以上', \
                    'skills': None, 'travel': '無需出差外派', 'management': '不需負擔管理責任', 'remote': '不可遠端工作', \
                    'category': ['軟體工程師'], 'job_source': 'https://www.104.com.tw/job/8495k', 'create_date': '2024-04-28 00:00:00'}
    
    category_list = ["軟體／工程類人員", "iOS工程師", "Android工程師", "前端工程師", "後端工程師", \
        "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", \
        "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", \
        "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", \
        "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", \
        "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", \
        "資料庫管理人員", "MIS／網管主管", "資安主管"]

    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是一個工作敘述檢查輸入員，會以台灣式的中文簡潔細心地提供每個職缺16個項目的內容"},
        {"role": "user", "content": f"""
        請用繁體中文、接近104人力銀行的敘述風格和以下json格式回答問題。
        回答json每個欄位都一定要有，格式= {empty_json}
        閱讀下面這個串列的job code和網頁工作敘述然後擷取我需要的內容，總共有很多筆資料
        格式是{list_form}

        {content}

        回覆中，以下每一個欄位都要有
        1.'job_title': 填寫工作職位名稱，可以是英文或中文
        2.'company_name'　保留原本語言
        3.'job_location'　在香港，要翻譯成香港的地名（例如：香港中環），中間不要空白
        4.'salary_period': 只能填寫：待遇面議（沒有資料），或是月薪多少HKD（例如：月薪13,000-16,000HKD，如果是年薪就換算成月薪）
        如果是annual pay，要轉換成月薪
        5.'min_salary': 只填寫數字，沒有的話不要寫，月薪最低的數字
        6.'max_salary': 只填寫數字，沒有的話不要寫，月薪最高的數字，如果只有一個數字那就和'min_salary'相同
        7.'edu_level' : 只能填寫：不拘、高中職、專科、大學、碩士、博士
        8.'work_experience': 只能填寫：不拘 或幾年以上（例如：1年以上、4年以上）
        9.'skills': 填寫程式語言和軟體相關的技能，請回覆簡潔的關鍵單字，中間用 ',' 分開，沒有的話回傳None
        10.'travel': 只能填寫：需出差外派　或　無需出差外派
        11.'management': 只能填寫：需負擔管理責任　或　不需負擔管理責任
        12.'remote': 只能填寫：可遠端工作　或　不可遠端工作
        13.'category': 一定要填寫，只能從category_list裡面的分類選1-3個適合的，至少要有一個，一字不差
        14.'create_date: '填{tw_date}，一字不差
        15.'job_code': 填串列裡的'job_code'，一字不差
        16.'job_source': 填"https://hk.jobsdb.com/job/+串列裡的'job_code'"，一字不差

        工作分類：["軟體／工程類人員", "iOS工程師", "Android工程師", "前端工程師", "後端工程師", 
            "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", 
            "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", 
            "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", 
            "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", 
            "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", 
            "資料庫管理人員", "MIS／網管主管", "資安主管"]

        回覆範例 = 每個工作有一個{example_json}，會變成一個list就像[{example_json},{example_json}]

        category_list = {category_list}
        """
        }])

    dict_response = ast.literal_eval(completion.choices[0].message)
    print(type(dict_response))
    print(dict_response)

def get_jd(job_code):
    url = f'https://hk.jobsdb.com/job/{job_code}'

    driver.get(url)
    
    # Get the page source
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    jd_ele = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR,'div.y735df0._1iz8dgs9y._1iz8dgs9r._1iz8dgsag._1iz8dgs8u._1iz8dgs8n._1iz8dgs9c')))
    jd = jd_ele.get_attribute("innerText")

    jd_info = [job_code, jd]
    
    # job_info = [job_title, job_code, company_name, job_location, salary_info, \
    #             min_salary, max_salary, edu_level, work_experience, skills, \
    #             travel, management, remote, url_to_jobsdb, job_category]

    return jd_info

def insert_sql(one_jd):

    db_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                            user=os.getenv("RDS_USER"),
                            password=os.getenv("RDS_PASSWORD"),
                            database=os.getenv("RDS_DB"),
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    cursor = db_conn.cursor()
    
    if db_conn and cursor:
        try:
            insert_query = """
                INSERT INTO job (job_title, job_code, company_name, job_location, salary_period, 
                            min_salary, max_salary, edu_level, work_experience, skills, 
                            travel, management, remote, job_source, create_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            job_title = VALUES(job_title),
                            company_name = VALUES(company_name),
                            job_location = VALUES(job_location),
                            salary_period = VALUES(salary_period),
                            min_salary = VALUES(min_salary),
                            max_salary = VALUES(max_salary),
                            edu_level = VALUES(edu_level),
                            work_experience = VALUES(work_experience),
                            skills = VALUES(skills),
                            travel = VALUES(travel),
                            management = VALUES(management),
                            remote = VALUES(remote),
                            job_source = VALUES(job_source),
                            create_date = VALUES(create_date)
                """
            print(one_jd['job_title'], one_jd['job_code'], one_jd['company_name'], one_jd['job_location'],one_jd['salary_period'], 
                one_jd['min_salary'], one_jd['max_salary'], one_jd['edu_level'],one_jd['work_experience'], one_jd['skills'], 
                one_jd['travel'], one_jd['management'], one_jd['remote'], one_jd['job_source'], one_jd['create_date'])
            cursor.execute(insert_query, (
                one_jd['job_title'], one_jd['job_code'], one_jd['company_name'], one_jd['job_location'],one_jd['salary_period'], 
                one_jd['min_salary'], one_jd['max_salary'], one_jd['edu_level'],one_jd['work_experience'], one_jd['skills'], 
                one_jd['travel'], one_jd['management'], one_jd['remote'], one_jd['job_source'], one_jd['create_date']
            ))
            print("insert jd")
            db_conn.commit()
        except Exception as e:
            logging.error(f"insert jd error, {e}")
            print(e)
            # db_conn.rollback()

        try:
        # Prepare the query for bulk insertion for job categories
            category_query = """
                INSERT INTO job_category (job_code, job_category)
                VALUES (%s, %s)
                """
            for j_category in one_jd['category']:
                cursor.execute(category_query, (one_jd['job_code'], j_category))
                db_conn.commit()
        except Exception as e:
            logging.error(f"insert jd_category error, {e}")

jd_infos = []

job_codes = crawl_job_codes()
print(len(job_codes))
for job_code in job_codes:
    try:
        jd = get_jd(job_code)
        data = get_gemini_summary(jd)
        insert_sql(data)
    except Exception as e:
        logging.error(f"Failed to process job {job_code}: {e}")
        continue
    time.sleep(5)

driver.quit()

# exjd = get_jd(75436629)
# get_openai_summary(exjd)
# insert_sql(75436629,exjd)
# driver.quit()
