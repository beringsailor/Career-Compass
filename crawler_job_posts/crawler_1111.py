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
    driver.get("https://www.1111.com.tw/job/113081067/")

    # set default results
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

    head = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui_job_detail")))
    job_title_ele = head.find_element(By.CSS_SELECTOR,"div.header_title_fixed")
    job_title = job_title_ele.text

    company_div = head.find_element(By.CSS_SELECTOR,"div.ui_card_company")
    company_ele = company_div.find_element(By.CSS_SELECTOR,"span.title_7")
    company_name = company_ele.text

    work_info_div = driver.find_element(By.CSS_SELECTOR, "div.content_items.job_info")

    salary_ele = work_info_div.find_element(By.CSS_SELECTOR, "span.job_info_content.color_Secondary_1")
    salary = salary_ele.text

    job_location_div = work_info_div.find_element(By.CSS_SELECTOR, "div.job_info_icon.icon_location")
    next_div = job_location_div.find_element(By.XPATH, "./following-sibling::div[1]")
    job_location_ele = next_div.find_elements(By.CSS_SELECTOR, "span.job_info_content")
    for j in job_location_ele:
        print(j )

    job_info = [job_title, company_name, salary, job_location]
    print(job_info)

get_job()