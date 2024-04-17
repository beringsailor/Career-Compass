import time
import random
import requests
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.1111.com.tw/search/job?d0=140506")
# driver.get("https://www.1111.com.tw/search/job?d0=140503")

def scroll_to_bottom(driver):
    old_height = driver.execute_script("return document.body.scrollHeight;")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # sleep randomly
        time.sleep(random.randint(1, 3))

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == old_height:
            break

        old_height = new_height

def crawl_jobs(driver):
    job_codes = []

    # scroll_to_bottom(driver)
    
    posts = driver.find_elements(By.CLASS_NAME, "item__job.job-item.card.work")
    for post in posts:
        pattern = r'/job/(\d+)/'

        job_div = driver.find_element(By.XPATH, "//div[@class='title position0']")
        a_tag = job_div.find_element(By.TAG_NAME,"a")
        job_link= a_tag.get_attribute("href")
        match = re.search(pattern, job_link)
        if match:
            job_code = match.group(1)
            job_codes.append(job_code)
        else:
            # Log a warning message
            logging.warning("No job code found for post: %s", post.text)
    
    return job_codes

# job_codes = crawl_jobs(driver)
# print("Total job codes:", len(job_codes))

def get_job():
    # driver.get("https://www.1111.com.tw/job/113081067/")
    # driver.get("https://www.1111.com.tw/job/112993204/")
    driver.get("https://www.1111.com.tw/job/91524616/")

    # set default results
    job_title = None
    company_name = None
    salary = None
    job_location = None
    job_category = None
    work_experience = None
    edu_level = None
    skills = None
    management = None
    travel = None
    remote = None

    head = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui_job_detail")))
    job_title_ele = head.find_element(By.CSS_SELECTOR,"div.header_title_fixed")
    job_title = job_title_ele.text

    company_div = head.find_element(By.CSS_SELECTOR,"div.ui_card_company")
    company_ele = company_div.find_element(By.CSS_SELECTOR,"span.title_7")
    company_name = company_ele.text

    # 工作資訊
    work_info_div = driver.find_element(By.CSS_SELECTOR, "div.content_items.job_info")

    salary_ele = work_info_div.find_element(By.CSS_SELECTOR, "span.job_info_content.color_Secondary_1")
    salary = salary_ele.text

    divs = work_info_div.find_elements(By.CSS_SELECTOR, "span.job_info_title")
    for div in divs:
        if div.text.strip() == "遠距工作：":
            remote_div = div.find_element(By.XPATH, "./following-sibling::span[1]")
            remote = remote_div.text

    job_location_div = work_info_div.find_element(By.CSS_SELECTOR, "div.job_info_icon.icon_location")
    next_div = job_location_div.find_element(By.XPATH, "./following-sibling::div[1]")
    job_location_ele = next_div.find_element(By.CSS_SELECTOR, "span.job_info_content")
    job_location = job_location_ele.text

    job_category = []
    job_category_div = work_info_div.find_element(By.CSS_SELECTOR, "span.job_info_content.btn-group")
    job_location_ele = job_category_div.find_elements(By.TAG_NAME, "u")
    for j_category in job_location_ele:
        job_category.append(j_category.text)
    
    # 要求條件
    work_exp_divs = driver.find_elements(By.CSS_SELECTOR, "div.content_items.job_skill span.job_info_title")
    for div in work_exp_divs: 
        spec_title = div.text

        if spec_title == "工作經驗：":
            following_div = div.find_element(By.XPATH, "following-sibling::span[1]")
            work_experience = following_div.text
        elif spec_title == "學歷限制：":
            following_div = div.find_element(By.XPATH, "following-sibling::span[1]")
            edu_level = following_div.text
        elif spec_title == "電腦專長：":
            following_div = div.find_element(By.XPATH, "following-sibling::span[1]")
            skill_divs = following_div.find_elements(By.TAG_NAME, "a")
            for div in skill_divs:
                if skills == None:
                    skills = str(div.text)
                else:
                    skills += "," + str(div.text)

    job_info = [job_title, company_name, job_location, salary,  \
                work_experience, edu_level, skills, travel, 
                management, remote, job_category]
    
    # job_info = [job_title, company_name, job_location, salary_info, min_salary, \
    #             max_salary, edu_level, work_experience, skills, travel, \
    #             management, remote, job_category]
    
    print(job_info)

get_job()