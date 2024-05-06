import time
import random
import requests
import re
import os
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
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC

from airflow.decorators import dag
from datetime import datetime
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

load_dotenv()

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver = webdriver.Remote("http://127.0.0.1:4444/wd/hub", service=Service(ChromeDriverManager().install()), options=options)

# all IT jobs
driver.get("https://www.518.com.tw/job-index.html?ab=2032001")

# crawl job_ids of each page
def crawl_each_page(driver):
    job_links_per_page = []

    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        posts = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.all_job_hover, div.all_job_hover.new_job")))

        for post in posts:
            h2 = post.find_element(By.CLASS_NAME, "job__title__inner")
            a_tag = h2.find_element(By.TAG_NAME, "a")
            job_link = a_tag.get_attribute("href")
            if job_link:
                job_links_per_page.append(job_link)
                print(job_link)
            else:
                logging.warning("No job link found for post: %s", post.text)
    except StaleElementReferenceException:
        # Retry if a stale element reference exception occurs
        return crawl_each_page(driver)
    
    return job_links_per_page

def crawl_all_pages(driver):
    all_job_links = []

    while True:
        # Extract job codes from the current page
        job_codes_per_page = crawl_each_page(driver)
        all_job_links.extend(job_codes_per_page)

        try:
            page_div = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.common-pagination")))
            next_button = page_div.find_element(By.CSS_SELECTOR, "a.goNext")
            if "is-disabled" in next_button.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", next_button)

            time.sleep(3)

            job_codes_per_page = crawl_each_page(driver)
            all_job_links.extend(job_codes_per_page)
        except NoSuchElementException:
            break

    return all_job_links

def get_job(url):
    driver.get(url)

    match = re.search(r'job-(\w+)\.html', url)
    if match:
        extracted_string = match.group(1)
        job_code = extracted_string
    
    # set default results
    job_code = job_code
    job_title = None
    company_name = None
    salary = None
    job_location = None
    job_category = None
    work_experience = None
    management = None
    travel = None
    edu_level = None
    skills = None
    remote = None
    url_to_518 = url
    
    # Get the page source
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    head = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.headContent")))

    job_title_ele = head.find_element(By.CSS_SELECTOR,"h1.job-title")
    job_title = job_title_ele.text

    h2 = head.find_element(By.CSS_SELECTOR,"div.company-info-container")
    company_info_ele = h2.find_element(By.CSS_SELECTOR,"span")
    company_name = company_info_ele.text

    # get job_details
    contents = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job-detail-box")))
    for content in contents:
        try:
            wrappers = content.find_elements(By.CSS_SELECTOR,"div.wrapper")
            for wrapper in wrappers:
                job_item_names = wrapper.find_elements(By.CLASS_NAME, "jobItemName")
                for job_item_name in job_item_names:
                    name = job_item_name.text
                    
                    if name == "薪資待遇":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        salary_info = following_div.text
                        match = re.search(r'月薪 (\d{1,3}(?:,\d{3})*) 至 (\d{1,3}(?:,\d{3})*)', salary_info)
                        if match:
                            min_salary = int(match.group(1).replace(",", "")) if match.group(1) else 0
                            max_salary = int(match.group(2).replace(",", "")) if match.group(2) else 0
                        else:
                            min_salary = 0
                            max_salary = 0
                    elif name == "上班地點":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        job_location = following_div.text
                    elif name == "職務類別":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        job_category_text = following_div.text
                        job_category = job_category_text.split('、')
                    elif name == "工作經驗":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        work_experience = following_div.text
                    elif name == "管理責任":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        management = following_div.text
                    elif name == "是否出差":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        travel = following_div.text
                    elif name == "教育程度":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        edu_level = following_div.text
                    elif name == "電腦專長":
                        following_div = job_item_name.find_element(By.XPATH, "following-sibling::div[1]")
                        skills = following_div.text
                    
        except NoSuchElementException:
            break  # Exit the loop if the "Next Page" button is not found
    
    job_info = [job_title, job_code, company_name, job_location, salary_info, \
                min_salary, max_salary, edu_level, work_experience, skills, \
                travel, management, remote, url_to_518, job_category]

    return job_info

def insert_sql(one_jd):
    # get taiwan date when inserting
    tw_time = datetime.now(UTC) + timedelta(hours=8)
    tw_date = tw_time.date()

    db_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                            user=os.getenv("RDS_USER"),
                            password=os.getenv("RDS_PASSWORD"),
                            database=os.getenv("RDS_DB"),
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    cursor = db_conn.cursor()

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

    job_data = [one_jd[0],one_jd[1],one_jd[2],one_jd[3],one_jd[4], \
                one_jd[5],one_jd[6],one_jd[7],one_jd[8],one_jd[9], \
                one_jd[10],one_jd[11],one_jd[12],one_jd[13],tw_date]
    
    # Execute the bulk insert
    cursor.execute(insert_query, job_data)
    db_conn.commit()
    
    category_query =  """
        INSERT IGNORE INTO job_category (job_code, job_category)
        VALUES (%s, %s)
        """

    for j_category in one_jd[14]:
        cursor.execute(category_query, (one_jd[1], j_category))
        db_conn.commit()



j_links = crawl_all_pages(driver)
print(len(j_links))

i = 0
for j_link in j_links:
    jd = get_job(j_link)
    insert_sql(jd)
    time.sleep(0.5)
    i += 1

# print(i)

# single_jd = get_job("https://www.518.com.tw/job-GQwxr6.html")
# insert_sql(single_jd)
# print(single_jd)

driver.quit()