import time
import random
import requests
import unicodedata
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

# blockchain SWE
driver.get("https://www.104.com.tw/jobs/search/?jobcat=2007001023")

# crawl job_ids of each page
def crawl_each_page(driver):
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
        return crawl_each_page(driver)
    
    return job_codes_per_page

# crawl through multiple pages
def crawl_all_pages(driver):
    all_job_codes = []

    while True:
        # Extract job codes from the current page
        job_codes_per_page = crawl_each_page(driver)
        all_job_codes.extend(job_codes_per_page)

        try:
            next_button = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")))
            next_button = driver.find_element(By.CLASS_NAME, "b-btn.b-btn--page.js-next-page")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            next_button.click() 
            
            job_codes_per_page = crawl_each_page(driver)
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
    job_location = data['data']['jobDetail']['addressArea']
    salary_info = data['data']['jobDetail']['salary']
    min_salary = data['data']['jobDetail']['salaryMin']
    max_salary = data['data']['jobDetail']['salaryMax']
    edu_level = data['data']['condition']['edu']
    work_experience = data['data']['condition']['workExp']
    # iterate for multiple skills
    skills = []
    for item in data['data']['condition']['specialty']:
        skills.append(item['description'])
    travel = data['data']['jobDetail']['businessTrip']
    management = data['data']['jobDetail']['manageResp']
    remote = []
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
                management, remote ,job_category]

    # # return data['data']
    # time.sleep(random.uniform(1, 3))

    return job_info

all_job_codes = crawl_all_pages(driver)
print("Total job codes:", len(all_job_codes))

all_jds = []
for j_code in all_job_codes:
    jd = get_job(j_code)
    all_jds.append(jd)

    time.sleep(1)

print("Total job descriptions:", len(all_jds))
print(all_jds)

# # example job pages
# get_job("87448")
# get_job("6kw77")

driver.quit()
