import re
import os
import ast
import time
import json
import boto3
import random
import logging
import requests
import pymysql
import concurrent.futures
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, ElementNotInteractableException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.support import expected_conditions as EC

# Used to securely store your API key
import google.generativeai as genai

start_time = datetime.now()

load_dotenv()

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

##### logging  #####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('crawler_dodax.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info('Start crawler_dodax.py')

logger.info('Start crawler_jobsdb.py')

# functions
start_time = datetime.now()

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--disable-blink-features=AutomationControlled')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_all_codes():
    all_job_codes = []
    page_num = 1

    # get total job post numbers
    url = f"https://doda-x.jp/job/search/?jobMiddleIds=1000000022"
    driver.get(url)
    upper_div = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-result__head")))
    span_element = upper_div.find_element(By.CSS_SELECTOR, "span.search-result__head-txt-cnt--1.ttl")
    number = span_element.text.strip()
    number = int(number)
    total_pages = (number // 30) + 1

    while page_num <= total_pages:
        try:
            offset = (page_num -1)*30
            url = f"https://doda-x.jp/job/search/?jobMiddleIds=1000000022&offset={offset}"
            driver.get(url)

            posts = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.result-list__item")))

            if posts:
                for link in posts:
                    a_tag = link.find_element(By.CSS_SELECTOR, "a.job-result-heading-link")
                    href_value = a_tag.get_attribute("href")
                    job_id_match = re.search(r'\d{10}', href_value)
                    if job_id_match:
                        job_id = job_id_match.group(0)
                        all_job_codes.append(job_id)
                        # time.sleep(1)
                    else:
                        logging.error("No job a_tag")
                logger.info(f"crawling page: {page_num}")
                page_num += 1
            else:
                break
        except Exception as e:
            logger.error(f"exception when crawling: {e}")
    return all_job_codes

def get_jd(job_code):
    url = f"https://doda-x.jp/job/detail/{job_code}/"
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "jobDetailJson")))
        html_content = driver.page_source
        
        soup = BeautifulSoup(html_content, 'html.parser')
        jd_json = soup.find('input', id='jobDetailJson')['value']

        jd_json_unescaped = BeautifulSoup(jd_json, 'html.parser').text
        jd_dict = json.loads(jd_json_unescaped)
    except Exception as e:
        logger.error(f"No jd for job code {job_code}")

    return jd_dict

def get_all_jd(code_list):
    total_count = len(code_list)
    all_jd = []
    for index, job_code in enumerate(code_list):
        logger.info(f"Now getting {job_code} JD {index + 1} of {total_count}")
        try:
            jd = get_jd(job_code)
            if jd:
                all_jd.append(jd)
                time.sleep(2)
        except Exception as e:
            logger.error(f"failed to get {job_code} raw_jd {index + 1} of {total_count}: {e}")
    return all_jd

# all_codes = get_all_codes()
# jd = get_all_jd(all_codes)

# print(len(all))
# print(all)

jd = get_jd(3010212845)
print(jd)

driver.quit()