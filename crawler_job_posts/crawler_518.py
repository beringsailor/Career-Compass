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
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# app SWE
driver.get("https://www.518.com.tw/job-index.html?ab=2032001016")

# # all IT jobs
# driver.get("https://www.518.com.tw/job-index.html?ab=2032001")

# crawl job_ids of each page
def crawl_each_page(driver):
    job_links_per_page = []

    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        posts = WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.all_job_hover, div.all_job_hover.new_job")))

        print(len(posts))
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

            # Wait for the next page to load
            time.sleep(3)  # Adjust this delay according to your page load time

            job_codes_per_page = crawl_each_page(driver)
            all_job_links.extend(job_codes_per_page)
        except NoSuchElementException:
            break  # Exit the loop if the "Next Page" button is not found

    return all_job_links

def get_job(url):
    driver.get(url)

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
    remote = None

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
                        salary = following_div.text
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
    
    job_info = [job_title, company_name, job_location, salary,\
                edu_level, work_experience, skills, travel, \
                management, remote, job_category]
    
    # job_info = [job_title, company_name, job_location, salary_info, min_salary, \
    #             max_salary, edu_level, work_experience, skills, travel, \
    #             management, remote, job_category]

    return job_info

job = get_job("https://www.518.com.tw/job-LXb23W.html")
print(job)

# j_links = crawl_all_pages(driver)
# print(len(j_links))

# job_details = []
# for j_link in j_links:
#     jd = get_job(j_link)
#     job_details.append(jd)
#     time.sleep(random.uniform(1, 3))

# print(job_details)
# print(len(job_details))

driver.quit()