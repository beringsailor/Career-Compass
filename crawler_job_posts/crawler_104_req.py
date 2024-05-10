import re
import os
import time
import json
import boto3
import random
import logging
import requests
import pymysql
import concurrent.futures
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

start_time = datetime.now()

load_dotenv()

##### logging  #####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('crawler_104_dag.log')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

logger.info('Start crawler_104.py')

def get_all_jcodes():
    """search jobs on 104"""
    total_jcodes = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
        'Referer': 'https://www.104.com.tw/jobs/search/',
    }

    url = 'https://www.104.com.tw/jobs/search/list'

    category_list = ['2007001013','2007001014','2007001015','2007001016','2007001017', \
                '2007001018','2007001020','2007001021','2007001022','2007002002']
    # category_list = ['2007001023']
    try:
        for category in category_list:
            logger.info(category)
            query = f'ro=0&kwop=7&expansionType=area,spec,com,job,wf,wktm&mode=s&jobsource=2018indexpoc&asc=0&jobcat={category}'
            page = 1
            while True:
                params = f'{query}&page={page}'

                r = requests.get(url, params=params, headers=headers)
                if r.status_code != requests.codes.ok:
                    data = r.json()
                    logging.error('job_code page request failed', r.status_code, data['status'], data['statusMsg'], data['errorMsg'])
                
                data = r.json()
                # total_count = data['data']['totalCount']
                logging.info(len(data['data']['list']))
                if len(data['data']['list']) == 0:
                    break

                pattern = r'\/job\/([a-zA-Z0-9]+)\?'
                for job in data['data']['list']:
                    job_link = job['link']['job']
                    match = re.search(pattern, job_link)
                    if match:
                        job_code = match.group(1)
                        if job_code not in total_jcodes:
                            total_jcodes.append(job_code)
                        logging.info(job_code)
                page +=1
                # print(data['data']['list'])
    except Exception as e:
        logging.error("fail to get job code from category list")

    return total_jcodes

def get_all_jd(jcode_list): 
    all_jds = []
    future_to_job = {}

    def get_job_info(job_id):
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
                        # only 3 characters? 
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
                        
                        r.close()
                        time.sleep(0.1)
                        return job_info
                    
                    except Exception as e:
                        logging.error(f'details for {url} request missing', {e})
                else:
                    logging.error(f'did not get jd from {url}, posting is closed')
            else:
                logging.error(f'request to {url} failed, status code={r.status_code}')
        except Exception as e:
            logging.error(f'get 104 jd, {url} request failed', {e})


    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for job_id in jcode_list:
            task = executor.submit(get_job_info, job_id)
            future_to_job[task] = job_id
        
        for future in concurrent.futures.as_completed(future_to_job):
            job_id = future_to_job[future]
            try:
                job_info = future.result()
                if job_info is not None:
                    all_jds.append(job_info)
            except Exception as e:
                logging.error(f'Job {job_id} generated an exception: {e}')

    return all_jds

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

        # print(all_temp_code)

        # delete records from main table that are not in the temporary table
        # ERROR:root:Error updating data table: (1205, 'Lock wait timeout exceeded; try restarting transaction')
        # sql_delete = """
        # DELETE FROM job
        # WHERE job_source LIKE '%www.104.com%'
        # AND create_date < '2024-05-08 00:00:00'
        # AND job_code NOT IN (
        #     SELECT job_code
        #     FROM temp_job
        # );
        # """

        sql_temp_job = "SELECT job_code FROM temp_job"
        cursor.execute(sql_temp_job)
        all_temp_code = cursor.fetchall()
        temp_job_codes = [d['job_code'] for d in all_temp_code]

        cursor.execute("START TRANSACTION")
        sql_delete = """
            DELETE FROM job
            WHERE job_source LIKE '%%www.104.com%%'
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

    filename = f"jd_104_{tw_date}.json"
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

total_codes = get_all_jcodes()
logger.info(f'total job_codes: {len(total_codes)}')

all_jd = get_all_jd(total_codes)
logger.info(f'total jds: {len(all_jd)}')

insert_sql(all_jd)
logger.info("inserted all 104 jd to db")

all_jd_json = list_to_json(all_jd)
logger.info("transformed all jd to json")

upload_to_s3(all_jd_json)
logger.info("uploaded today's 104 json")

logger.info("Done")

end_time = datetime.now()
logger.info(f"start and end time: {start_time}, {end_time}")