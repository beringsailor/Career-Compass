import time
import random
import requests
import unicodedata
from datetime import datetime, timedelta, UTC
import pymysql
import sys
import os
import re
import boto3
import logging
import json
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from logging.handlers import TimedRotatingFileHandler

# # to produce log
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# handler = TimedRotatingFileHandler(filename='example.log', when='midnight', interval=1, backupCount=7)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# to start crawling
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# can't be headless, will be blocked
# options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# blockchain SWE
# driver.get("https://www.104.com.tw/jobs/search/?jobcat=2007001023")
driver.get("https://www.104.com.tw/jobs/search/?jobcat=2007001022")

# crawl job_ids of each page
def crawl_id_each_page(driver):
    job_codes_per_page = []

    try:
        posts = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "b-block--top-bord.job-list-item.b-clearfix.js-job-item")))
        for post in posts:
            # Not extract the first 2 commercial recommended posts
            if "js-job-item--focus" not in post.get_attribute("class"):
                pattern = r'job/(\w+)\?'

                job_element = WebDriverWait(post, 30).until(EC.element_to_be_clickable((By.XPATH, ".//a[@data-qa-id='jobSeachResultTitle' and contains(@class, 'js-job-link')]")))
                job_link= job_element.get_attribute("href")
                match = re.search(pattern, job_link)
                if match:
                    job_code = match.group(1)
                    job_codes_per_page.append(job_code)
                else:
                    # Log a warning message
                    logging.warning("No job code found for post: %s", post.text)
    except StaleElementReferenceException:
        # Retry if a stale element reference exception occurs
        return crawl_id_each_page(driver)
    
    return job_codes_per_page

# crawl through multiple pages
def crawl_id_all_pages(driver):
    all_job_codes = []

    while True:
        # Extract job codes from the current page
        job_codes_per_page = crawl_id_each_page(driver)
        all_job_codes.extend(job_codes_per_page)

        try:
            next_button = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")))
            next_button = driver.find_element(By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            next_button.click() 
            
            job_codes_per_page = crawl_id_each_page(driver)
            all_job_codes.extend(job_codes_per_page)

            # Wait for the next page to load
            time.sleep(2)  # Adjust this delay according to your page load time
        except ElementNotInteractableException:
            break  # Exit the loop if the "Next Page" button is not found

    return all_job_codes

# get job details
def get_job(job_id):
    url = f'https://www.104.com.tw/job/ajax/content/{job_id}'

    # set default results to None
    job_title = None
    company_name = None
    job_location = None
    salary_info = None
    min_salary = None
    max_salary = None
    edu_level = None
    work_experience = None
    skills = None
    travel = None
    management = None
    remote = None
    job_category = None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
        'Referer': f'https://www.104.com.tw/job/{job_id}'
    }

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        logging.warning('get 104 jd request failed', r.status_code)

    data = r.json()
    # print(data['data'])

    job_title = data['data']['header']['jobName']
    company_name = data['data']['header']['custName']
    # only 3 characters? 
    job_location = data['data']['jobDetail']['addressArea']
    salary_info = data['data']['jobDetail']['salary']
    min_salary = data['data']['jobDetail']['salaryMin']
    max_salary = data['data']['jobDetail']['salaryMax']
    edu_level = data['data']['condition']['edu']
    work_experience = data['data']['condition']['workExp']
    # iterate for multiple skills
    for item in data['data']['condition']['specialty']:
        if skills is None:
            skills = str(item['description'])
        else:
            skills += "," + str(item['description'])
    if data['data']['jobDetail']['businessTrip'] != None:
        travel = data['data']['jobDetail']['businessTrip']
    management = data['data']['jobDetail']['manageResp']
    if data['data']['jobDetail']['remoteWork'] != None:
        remote = '可遠端工作'
    else:
        remote = '不可遠端工作'
    # iterate for multiple categories
    job_category = []
    for item in data['data']['jobDetail']['jobCategory']:
        job_category.append(item['description'])
    
    job_info = [job_title, company_name, job_location, salary_info, min_salary, \
                max_salary, edu_level, work_experience, skills, travel, \
                management, remote, job_category]
    
    # job_info_s3 = {
    # 'job_title': job_title, 
    # 'company_name': company_name, 
    # 'job_location': job_location, 
    # 'salary_info': salary_info, 
    # 'min_salary': min_salary, 
    # 'max_salary': max_salary, 
    # 'edu_level': edu_level, 
    # 'work_experience': work_experience, 
    # 'skills': skills, 
    # 'travel': travel,
    # 'management': management, 
    # 'remote': remote, 
    # 'job_category': job_category
    # }  

    # # return data['data']
    # time.sleep(random.uniform(1, 3))

    return job_info

# insert each job to database
def insert_sql(one_job_jd):
    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    insert_query = \
    """""""""
    INSERT INTO job (job_title, company_name, job_location, salary_period, min_salary, 
                    max_salary, edu_level, work_experience, skills, travel, 
                    management, remote, job_source, create_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """""""""
    cursor.execute(insert_query, (one_job_jd[0], one_job_jd[1], one_job_jd[2], one_job_jd[3], one_job_jd[4], \
                                    one_job_jd[5], one_job_jd[6], one_job_jd[7], one_job_jd[8], one_job_jd[9], \
                                    one_job_jd[10], one_job_jd[11], '104', tw_date))
    db_mysql_conn.commit()

    last_id = cursor.lastrowid
    for j_category in one_job_jd[12]:
        insert_query = "INSERT INTO job_category (job_id, job_category) VALUES (%s, %s)"
        cursor.execute(insert_query, (last_id, j_category))

        db_mysql_conn.commit()

# jd_list to json file
def list_to_json(input_list):
    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    filename = f"jd_104_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(input_list, json_file, ensure_ascii=False, indent=4)

    return filename

# upload_s3 for backup
def upload_to_s3(filename, BUCKET_NAME):
    try:
        s3.upload_file(filename, BUCKET_NAME, filename)
        result = 'uploaded to S3'
        return result
    except Exception as e:
        return {"errors": str(e)}

load_dotenv()

# access s3 bucket
s3 = boto3.client("s3", 
    region_name=os.getenv("REGION_NAME"),
    aws_access_key_id=os.getenv("S3_KEY"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY"))
BUCKET_NAME = os.getenv("S3_BUCKET")

# Connect to MySQL database
db_mysql_conn = pymysql.connect(host=os.getenv("MYSQL_HOST"),
                                user=os.getenv("MYSQL_USER"),
                                password=os.getenv("MYSQL_PASSWORD"),
                                database=os.getenv("MYSQL_DB"),
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

# # Connect to AWS RDS
# db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
#                                 user=os.getenv("RDS_USER"),
#                                 password=os.getenv("RDS_PASSWORD"),
#                                 database=os.getenv("RDS_DB"),
#                                 charset='utf8mb4',
#                                 cursorclass=pymysql.cursors.DictCursor)

cursor = db_mysql_conn.cursor()

all_job_codes = crawl_id_all_pages(driver)
print("Total job codes:", len(all_job_codes))

all_jds = []
for j_code in all_job_codes:
    jd = get_job(j_code)
    insert_sql(jd)

    all_jds.append(jd)
    time.sleep(1)

all_jd_filename = list_to_json(all_jds)
result = upload_to_s3(all_jd_filename, BUCKET_NAME)
print(result)

#     time.sleep(1)
# print('got all jd')

# for j_code in all_job_codes:
#     jd, jd_s3 = get_job(j_code)
#     insert_sql(jd)
#     time.sleep(1)

job_malay = get_job("889kc")
print(job_malay)

db_mysql_conn.close()
driver.quit()
