import time
import random
import requests
import re
import os
import json
import boto3
import logging
import pymysql
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

##### logging  #####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('crawler_518_dag.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info('Start crawler_518.py')

# functions
start_time = datetime.now()

def get_all_links():
    all_job_links = []
    page_num = 1

    while True:
        try:
            url = f"https://www.518.com.tw/job-index-P-{page_num}.html?ab=2032001,2032002"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            job_articles = soup.select('div.all_job_hover, div.all_job_hover.new_job')

            if job_articles:
                for job_article in job_articles:
                    h2 = job_article.find(class_="job__title__inner")
                    if h2:
                        a_tag = h2.find('a')
                        if a_tag and 'href' in a_tag.attrs:
                            job_link = a_tag.get('href')
                            all_job_links.append(job_link)
                    else:
                        logger.info(f"no link for job_article")
                logger.info(f"crawling page: {page_num}")
                page_num +=1
            else:
                break
        except Exception as e:
            logger.error(f"exception when crawling: {e}")
    return all_job_links

def get_jd(url):
    # Fetch the webpage content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract job code from URL
    match = re.search(r'job-(\w+)\.html', url)
    if match:
        job_code = match.group(1)
    else:
        job_code = None

    # Set default results
    job_title = None
    company_name = None
    salary_info = None
    min_salary = 0
    max_salary = 0
    job_location = None
    job_category = None
    work_experience = None
    management = None
    travel = None
    edu_level = None
    skills = None
    remote = None
    url_to_518 = url

    # Extract job title and company name
    job_title_element = soup.find("h1", class_="job-title")
    if job_title_element:
        job_title = job_title_element.text.strip()

    company_info_element = soup.find("div", class_="company-info-container")
    if company_info_element:
        company_name_element = company_info_element.find("span")
        if company_name_element:
            company_name = company_name_element.text.strip()

    # Extract job details
    job_detail_elements = soup.select("div.job-detail-box div.wrapper")
    for detail_element in job_detail_elements:
        job_item_names = detail_element.find_all(class_="jobItemName")
        for job_item_name in job_item_names:
            name = job_item_name.text.strip()
            following_div = job_item_name.find_next_sibling("div")
            if following_div:
                value = following_div.text.strip()
                if name == "薪資待遇":
                    match = re.search(r'月薪 (\d{1,3}(?:,\d{3})*) 至 (\d{1,3}(?:,\d{3})*)', value)
                    if match:
                        min_salary = int(match.group(1).replace(",", "")) if match.group(1) else 0
                        max_salary = int(match.group(2).replace(",", "")) if match.group(2) else 0
                    salary_info = value
                elif name == "上班地點":
                    job_location = value
                elif name == "職務類別":
                    job_category = value.split('、')
                elif name == "工作經驗":
                    work_experience = value
                elif name == "管理責任":
                    management = value
                elif name == "是否出差":
                    travel = value
                elif name == "教育程度":
                    edu_level = value
                elif name == "電腦專長":
                    skills = value

    # Assemble job information into a list
    job_info = [job_title, job_code, company_name, job_location, salary_info,
                min_salary, max_salary, edu_level, work_experience, skills,
                travel, management, remote, url_to_518, job_category]

    return job_info

def get_all_jd(code_list):
    all_jd = []
    for job_code in code_list:
        try:
            jd = get_jd(job_code)
            all_jd.append(jd)
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"failed to get raw_jd")
    return all_jd

def insert_sql(all_jd_list):
    # Connect to AWS RDS
    db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                                    user=os.getenv("RDS_USER"),
                                    password=os.getenv("RDS_PASSWORD"),
                                    database=os.getenv("RDS_DB"),
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
    if db_mysql_conn is None:
        logging.error("failed to connect to database")
    
    try:
        cursor = db_mysql_conn.cursor()

        # get taiwan date when inserting
        tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
        tw_date = tw_time.date()
        logger.info(f"taiwan date = {tw_date}")

        # insert temp_jobs
        cursor.execute("""
            CREATE TEMPORARY TABLE temp_job LIKE job;
        """)
        logger.info("temp_job table created")

        job_data = [(jd[0], jd[1], jd[2], jd[3], jd[4], jd[5], jd[6], jd[7], jd[8], jd[9], jd[10], jd[11], jd[12], jd[13], tw_date) for jd in all_jd_list]

        insert_temp_query = """
            INSERT INTO temp_job (job_title, job_code, company_name, job_location, salary_period, 
                            min_salary, max_salary, edu_level, work_experience, skills, 
                            travel, management, remote, job_source, create_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Execute the bulk insert
        cursor.executemany(insert_temp_query, job_data)
        db_mysql_conn.commit()
        logger.info("job_temp inserted")
        
        # insert temp_job_category
        cursor.execute("""
            CREATE TEMPORARY TABLE temp_job_category LIKE job_category;
        """)
        logger.info("temp_jobcat table created")

        category_data = [(jd[1], category) for jd in all_jd_list for category in jd[14]]

        # Prepare the query for bulk insertion for job categories
        insert_category_query = """
            INSERT INTO temp_job_category (job_code, job_category) 
            VALUES (%s, %s)
        """

        # Execute the bulk insert for job categories
        cursor.executemany(insert_category_query, category_data)
        db_mysql_conn.commit()
        logger.info("temp_jobcat table inserted")

        # check if the temporary table is empty
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM temp_job")
        result = cursor.fetchone()
        if result['cnt'] == 0:
            logging.error("No data in temp_job table.")
            return
        logger.info("temp_job table is not empty")


        # Prepare the query for bulk insertion
        upsert_job_query = """
            INSERT INTO job (job_title, job_code, company_name, job_location, salary_period, 
                            min_salary, max_salary, edu_level, work_experience, skills, 
                            travel, management, remote, job_source, create_date)
            SELECT job_title, job_code, company_name, job_location, salary_period, 
            min_salary, max_salary, edu_level, work_experience, skills, 
            travel, management, remote, job_source, create_date
            FROM temp_job
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
        cursor.execute(upsert_job_query)
        db_mysql_conn.commit()
        logger.info("job upserted")

        upsert_jobcat_query = """
            INSERT INTO job_category (job_code, job_category)
            SELECT job_code, job_category
            FROM temp_job_category
            ON DUPLICATE KEY UPDATE
                job_code = VALUES(job_code),
                job_category = VALUES(job_category);
        """
        
        cursor.execute(upsert_jobcat_query)
        db_mysql_conn.commit()
        logger.info("jobcat upserted")

        sql_temp_job = "SELECT job_code FROM temp_job"
        cursor.execute(sql_temp_job)
        all_temp_code = cursor.fetchall()
        temp_job_codes = [d['job_code'] for d in all_temp_code]

        cursor.execute("START TRANSACTION")
        sql_delete = """
            DELETE FROM job
            WHERE job_source LIKE '%%www.518.com.tw%%'
            AND job_code NOT IN ({})
        """.format(', '.join(['%s'] * len(temp_job_codes)))

        cursor.execute(sql_delete, temp_job_codes)
        cursor.execute("COMMIT")
        logger.info("job removed deleted and updated")

        logging.info("jd_data updated and cleaned.")
        db_mysql_conn.close()
    except Exception as e:
        logging.error(f"Error updating data table: {e}")
        db_mysql_conn.rollback()

# jd_list to json file
def list_to_json(input_list):
    # get taiwan date when inserting
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    tw_date = tw_time.date()

    keys = [
    "job_title","job_code","company_name","job_location","salary_period", \
    "min_salary","max_salary","edu_level","work_experience","skills", \
    "travel","management","remote","job_source","job_category" \
    ]

    modified_data = []
    for jd_value in input_list:
        modified_item = {k: v for k, v in zip(keys, jd_value)}
        modified_data.append(modified_item)

    filename = f"jd_518_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(input_list, json_file, ensure_ascii=False, indent=4)

    return filename

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


all_links = get_all_links()
logger.info(f'total job_links: {len(all_links)}')

all_jd = get_all_jd(all_links)
logger.info(f'total jds: {len(all_jd)}')

insert_sql(all_jd)
logger.info("inserted all 518 jd to db")

all_jd_json = list_to_json(all_jd)
logger.info("transformed all jd to json")

upload_to_s3(all_jd_json)
logger.info("uploaded today's 518 json")

logger.info("Done")

end_time = datetime.now()
logger.info(f"start and end time: {start_time}, {end_time}")

