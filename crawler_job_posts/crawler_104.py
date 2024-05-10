import time
import random
import requests
from datetime import datetime, timedelta, UTC
import threading
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
from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from logging.handlers import TimedRotatingFileHandler

# # to produce log
# if not os.path.exists("Logs"):
#     os.makedirs("Logs")

##### logging  #####
logging.basicConfig(level=logging.INFO, \
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', \
                    filename='crawler_104.log')
logger = logging.getLogger(__name__)
logger.info('Start crawler_518.py')

# start crawling
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# crawl all ids
def crawl_all_id(driver, category):
    
    all_job_codes = []
                     
    url = f'https://www.104.com.tw/jobs/search/?jobcat={category}'
    driver.get(url)

    while True:
        # Extract job codes from the current page
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
                        if job_code not in all_job_codes:
                            all_job_codes.append(job_code)
                    else:
                        logger.error("No job code found for post: %s", post.text)
        except StaleElementReferenceException or WebDriverException as e:
            logger.error(f"Error occurred: {e}")

        # turn page and crawl till last page
        try:
            next_button = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")))
            next_button = driver.find_element(By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            next_button.click() 
            
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
                            if job_code not in all_job_codes:
                                all_job_codes.append(job_code)
                        else:
                            logger.error("No job code found for post: %s", post.text)
            except StaleElementReferenceException or WebDriverException as e:
                logger.error(f"Error occurred: {e}")

            # Wait for the next page to load
            time.sleep(1)
        except ElementNotInteractableException:
            break  # Exit the loop if the "Next Page" button is not found

    return all_job_codes

# get job details
def get_all_jd(job_id_list): 
    all_jds = []
    for job_id in job_id_list:
        try:
            url = f'https://www.104.com.tw/job/ajax/content/{job_id}'

            # set default results to None
            job_title = None
            job_code = job_id
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
            url_to_104 = f'https://www.104.com.tw/job/{job_id}'

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
                'Referer': f'https://www.104.com.tw/job/{job_id}'
            }
            r = requests.get(url, headers=headers)
            if r.status_code == 200:

                data = r.json()
                
                if data['data']['switch'] == 'on':
                    try:
                        job_title = data['data']['header']['jobName']
                        company_name = data['data']['header']['custName']
                        # only 3 characters
                        job_location = data['data']['jobDetail']['addressRegion']
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
                        
                        job_info = [job_title, job_code, company_name, job_location, salary_info, \
                                    min_salary, max_salary, edu_level, work_experience, skills, \
                                    travel, management, remote, url_to_104, job_category]

                        all_jds.append(job_info)
                        r.close()
                        time.sleep(0.01)
                    except Exception as e:
                        logger.error(f'get 104 jd, {url} request failed', {e})
                else:
                    logger.error(f'did not get jd from {url}, posting is closed')
        except Exception as e:
            logger.error(f'get 104 jd, {url} request failed', {e})
    return all_jds

# insert each job to database
def insert_sql(all_jd_list):
    # Connect to AWS RDS
    db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                                    user=os.getenv("RDS_USER"),
                                    password=os.getenv("RDS_PASSWORD"),
                                    database=os.getenv("RDS_DB"),
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

    cursor = db_mysql_conn.cursor()

    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    job_data = [(jd[0], jd[1], jd[2], jd[3], jd[4], jd[5], jd[6], jd[7], jd[8], jd[9], jd[10], jd[11], jd[12], jd[13], tw_date) for jd in all_jd_list]

    # Prepare the query for bulk insertion
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

    # Execute the bulk insert
    cursor.executemany(insert_query, job_data)
    db_mysql_conn.commit()

    # Now, for job categories
    category_data = [(jd[1], category) for jd in all_jd_list for category in jd[14]]

    # Prepare the query for bulk insertion for job categories
    insert_category_query = """
        INSERT INTO job_category (job_code, job_category) 
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
        job_code = VALUES(job_code),
        job_category = VALUES(job_category)
        """
    
    # Execute the bulk insert for job categories
    cursor.executemany(insert_category_query, category_data)
    db_mysql_conn.commit()
    
    # for one_job_jd in all_jd_list:
    #     insert_query = \
    #     """
    #     INSERT INTO job (job_title, job_code, company_name, job_location, salary_period, 
    #                     min_salary, max_salary, edu_level, work_experience, skills, 
    #                     travel, management, remote, job_source, create_date)
    #                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    #                     ON DUPLICATE KEY UPDATE
    #                     job_title = VALUES(job_title),
    #                     company_name = VALUES(company_name),
    #                     job_location = VALUES(job_location),
    #                     salary_period = VALUES(salary_period),
    #                     min_salary = VALUES(min_salary),
    #                     max_salary = VALUES(max_salary),
    #                     edu_level = VALUES(edu_level),
    #                     work_experience = VALUES(work_experience),
    #                     skills = VALUES(skills),
    #                     travel = VALUES(travel),
    #                     management = VALUES(management),
    #                     remote = VALUES(remote),
    #                     job_source = VALUES(job_source),
    #                     create_date = VALUES(create_date);
    #     """
    #     cursor.execute(insert_query, (one_job_jd[0], one_job_jd[1], one_job_jd[2], one_job_jd[3], one_job_jd[4], \
    #                                     one_job_jd[5], one_job_jd[6], one_job_jd[7], one_job_jd[8], one_job_jd[9], \
    #                                     one_job_jd[10], one_job_jd[11], one_job_jd[12], one_job_jd[13], tw_date))
    #     db_mysql_conn.commit()

    #     for j_category in one_job_jd[12]:
    #         insert_query = "INSERT INTO job_category (job_code, job_category) VALUES (%s, %s)"
    #         cursor.execute(insert_query, (one_job_jd[1], j_category))

    #         db_mysql_conn.commit()

    db_mysql_conn.close()

# jd_list to json file
def list_to_json(input_list, category):
    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    filename = f"jd_104_{category}_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(input_list, json_file, ensure_ascii=False, indent=4)

    return filename

# upload_s3 for backup
def upload_to_s3(filename):
    # access s3 bucket
    s3 = boto3.client("s3", 
        region_name=os.getenv("REGION_NAME"),
        aws_access_key_id=os.getenv("S3_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY"))
    BUCKET_NAME = os.getenv("S3_BUCKET")
    
    try:
        s3.upload_file(filename, BUCKET_NAME, filename)
        result = 'uploaded to S3'
        return result
    except Exception as e:
        return {"errors": str(e)}

load_dotenv()

# iOS工程師, Android工程師, 前端工程師, 後端工程師, 全端工程師
# 數據分析師, 資料科學家, 資料工程師, AI工程師, 資料庫管理人員
category_list = ['2007001013','2007001014','2007001015','2007001016','2007001017', \
                '2007001018','2007001021','2007001022','2007001020','2007002002']

# category_list = ['2007001023']
# category_list = ['2007001016', \
#                 '2007001018','2007001021','2007001022','2007001020','2007002002']

for category in category_list:
    all_job_codes = crawl_all_id(driver, category)
    logger.info(f"Total {category} job codes:", len(all_job_codes))

    all_jd = get_all_jd(all_job_codes)
    logger.info(f"Total {category} jds:", len(all_jd))

    insert_sql(all_jd)
    logger.info(f'inserted {category} all jd')

    all_jd_filename = list_to_json(all_jd, category)
    result = upload_to_s3(all_jd_filename)
    logger.info(f"uploaded to today's {category} jd to s3")

driver.quit()

logger.info("Done for crawling 104")