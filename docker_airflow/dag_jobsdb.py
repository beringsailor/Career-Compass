from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

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

# Used to securely store your API key
import google.generativeai as genai

load_dotenv()

# s3 and database
s3 = boto3.client("s3", 
    region_name=os.getenv("REGION_NAME"),
    aws_access_key_id=os.getenv("S3_KEY"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY"))
BUCKET_NAME = os.getenv("S3_BUCKET")

db_host=os.getenv("RDS_HOST")
db_user=os.getenv("RDS_USER")
db_password=os.getenv("RDS_PASSWORD")
db_database=os.getenv("RDS_DB")

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

##### logging  #####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('crawler_jobsdb_dag.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info('Start crawler_jobsdb.py')

# functions
start_time = datetime.now()

def get_all_codes():
    all_job_codes = []
    page_num = 1

    while True:
        try:
            # url = f"https://hk.jobsdb.com/jobs-in-government-defence?page={page_num}"
            url = f"https://hk.jobsdb.com/jobs-in-information-communication-technology?daterange=14&page={page_num}"
            response = requests.get(url)
            if response.status_code != requests.codes.ok:
                logger.error(f'job_code page request failed')
                if response.status_code == 429:
                    # Extract rate limit information from headers
                    limit = response.headers.get('X-RateLimit-Limit')
                    remaining = response.headers.get('X-RateLimit-Remaining')
                    reset = response.headers.get('X-RateLimit-Reset')
                    logger.error(f"X-RateLimit-Limit= {limit} , 'X-RateLimit-Remaining'={remaining}, 'X-RateLimit-Reset'={reset}")
            soup = BeautifulSoup(response.text, 'html.parser')

            job_articles = soup.find_all('article', class_='y735df0 y735df1 _1iz8dgs7i _1iz8dgs6e _1iz8dgs9q _1iz8dgs8m _1iz8dgsh _1iz8dgs66 _1iz8dgs5e _12jtennb _12jtenn9 _12jtenna _94v4w18 _94v4w1b _1iz8dgs32 _1iz8dgs35')
            
            if job_articles:
                for job_article in job_articles:
                    job_div = job_article.find('div', class_=['y735df0', '_1iz8dgs4y', '_1iz8dgs4w'])
                    a_tag = job_div.find('a', {'data-automation': 'job-list-view-job-link'})
                    if a_tag:
                        # Get the href attribute of the <a> tag
                        job_link = a_tag.get('href')
                        if job_link:
                            pattern = r'/job/(\d+)\?'
                            matches = re.findall(pattern, job_link)
                            if matches:
                                # Extract the first match
                                job_code = matches[0]
                                # print(job_code)
                                all_job_codes.append(job_code)
                        else:
                            logger.error("No job link found for post")
                    else:
                        logger.error("No job a_tag")
                logger.info(f"crawling page: {page_num}")
                page_num +=1
            else:
                break
        except Exception as e:
            logger.error(f"exception when crawling: {e}")
    return all_job_codes

def get_jd(job_code):
    url = f"https://hk.jobsdb.com/job/{job_code}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    jd_ele = soup.find('div', class_='y735df0 _1iz8dgs9y _1iz8dgs9r _1iz8dgsag _1iz8dgs8u _1iz8dgs8n _1iz8dgs9c')

    if jd_ele:
        jd = jd_ele.get_text(strip=True)
        jd_info = [job_code, jd]
    else:
        logger.error(f"failed to get jd text for job code: {job_code}")

    return jd_info

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

def get_gemini_summary(content): 

    empty_json = {'job_code': '', 'job_title': '', 'company_name': '', 'job_location': '', 'salary_period': '', \
                'min_salary': 0, 'max_salary': 0, 'edu_level': '', 'work_experience': '', 'skills': '', \
                'travel': '', 'management': '', 'remote': '', 'category':[], 'job_source': '', \
                'create_date':''}

    response_json = {'job_code': '8495k', 'job_title': 'Senior/Principal Data Scientist 資深資料科學家', 'company_name': '瑞健股份有限公司', 'job_location': '桃園市蘆竹區', 'salary_period': '待遇面議', \
                    'min_salary': 0, 'max_salary': 0, 'edu_level': '大學以上', 'work_experience': '5年以上', 'skills': 'Java,C++,C#,J2EE,Python', \
                    'travel': '無需出差外派', 'management': '不需負擔管理責任', 'remote': '不可遠端工作', 'category': ['軟體／工程類人員'], 'job_source': 'https://hk.jobsdb.com/job/75519058', \
                    'create_date': '2024-04-28 00:00:00'}
    
    category_list = ["iOS工程師", "Android工程師", "前端工程師", "後端工程師", \
        "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", \
        "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", \
        "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", \
        "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", \
        "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", \
        "資料庫管理人員", "MIS／網管主管", "資安主管", "軟體／工程類人員"]

    # get taiwan date when inserting
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    tw_date = tw_time.date()
    
    prompt = f"""
    一定要用繁體中文、接近104人力銀行的敘述風格，和包含16個條件的回答問題。
    一定要符合 = {empty_json}，curly brackets前不要有任何文字
    回傳範例格式 = {response_json}
    閱讀下面這個串列的job code和網頁工作敘述然後擷取我需要的內容，總共有很多筆資料

    {content}

    1.'job_title': 填寫工作職位名稱，可以是英文或中文
    2.'company_name'　保留原本語言
    3.'job_location'　在香港，要翻譯成香港的地名（例如：香港中環），中間不要空白
    4.'salary_period': 只能填寫：待遇面議（沒有資料），或是月薪多少HKD（例如：月薪13,000-16,000HKD，如果是年薪就換算成月薪）
    如果是annual pay，要轉換成月薪
    5.'min_salary': 只填寫數字，沒有的話不要寫，月薪最低的數字
    6.'max_salary': 只填寫數字，沒有的話不要寫，月薪最高的數字，如果只有一個數字那就和'min_salary'相同
    7.'edu_level'： 只能填寫：不拘、高中職、專科、大學、碩士、博士
    8.'work_experience'：只能填寫：不拘 或幾年以上（例如：1年以上、4年以上）
    9.'skills'：請填寫程式語言和軟體相關的技能，關鍵單字，最多不超2個詞，沒有的話回傳None
    10.'travel'：只能填寫：需出差外派　或　無需出差外派
    11.'management'：只能填寫：需負擔管理責任　或　不需負擔管理責任
    12.'remote'只能填寫：可遠端工作　或　不可遠端工作
    13.'category'：一定要填寫，只能從category_list裡選1-3個適合的，至少要有一個，一字不差
    14.'create_date'：填{tw_date}，一字不差
    15.'job_code'：填串列裡的'job_code'，一字不差
    16.'job_source'：填"https://hk.jobsdb.com/job/'job_code'"（例如："https://hk.jobsdb.com/job/75431589"），一字不差

    工作分類：["軟體／工程類人員", "iOS工程師", "Android工程師", "前端工程師", "後端工程師", 
        "全端工程師", "數據分析師", "軟體工程師", "軟體助理工程師", "軟體專案主管", "系統分析師", 
        "資料科學家", "資料工程師", "AI工程師", "演算法工程師", "韌體工程師", "電玩程式設計師", 
        "Internet程式設計師", "資訊助理", "區塊鏈工程師", "BIOS工程師", "通訊軟體工程師", 
        "電子商務技術主管", "其他資訊專業人員", "MIS／網管類人員", "系統工程師", "網路管理工程師", 
        "資安工程師", "資訊設備管制人員", "雲端工程師", "網路安全分析師", "MES工程師", "MIS程式設計師", 
        "資料庫管理人員", "MIS／網管主管", "資安主管"]

    category_list = {category_list}
    """
    
    response = model.generate_content(prompt)

    try:
        response = response.text
        dict_response = eval(response)
        return dict_response
    except ValueError as e:
        logger.error(f"gemini failed to form dict response:{e}")

def process_all_jd(all_jd):
    total_count = len(all_jd)
    all_processed_jds = []
    for index, jd in enumerate(all_jd):
        logger.info(f"Now gemini processing JD {index + 1} of {total_count}")
        try:
            jd = get_gemini_summary(jd)
            all_processed_jds.append(jd)
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to get JD {index + 1} of {total_count}: {e}")
    return all_processed_jds

def raw_jd_to_json(input_list):
    # get taiwan date when inserting
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    tw_date = tw_time.date()

    filename = f"jd_jobsdb_raw_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(input_list, json_file, ensure_ascii=False, indent=4)

    return filename

# jd_list to json file
def processed_jd_to_json(input_list):
    # get taiwan date when inserting
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    tw_date = tw_time.date()

    filename = f"jd_jobsdb_processed_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump((input_list), json_file, ensure_ascii=False, indent=4)

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

def insert_sql(all_jd_list):
    # Connect to AWS RDS
    db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                                    user=os.getenv("RDS_USER"),
                                    password=os.getenv("RDS_PASSWORD"),
                                    database=os.getenv("RDS_DB"),
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
    if db_mysql_conn is None:
        logger.error("failed to connect to database")
    
    try:
        cursor = db_mysql_conn.cursor()

        # get taiwan date when inserting
        tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
        tw_date = tw_time.date()
        logger.info(tw_date)

        # insert create temp_job and temp_job_category
        cursor.execute("""
            CREATE TEMPORARY TABLE temp_job LIKE job;
        """)
        logger.info("temp_job table created")

        # insert temp_job_category
        cursor.execute("""
            CREATE TEMPORARY TABLE temp_job_category LIKE job_category;
        """)
        logger.info("temp_jobcat table created")

        # insert_temp_query = f"""
        #     INSERT INTO temp_job (
        #         job_title, job_code, company_name, job_location, salary_period, 
        #         min_salary, max_salary, edu_level, work_experience, skills, 
        #         travel, management, remote, job_source, create_date
        #     ) VALUES (
        #         %(job_title)s, %(job_code)s, %(company_name)s, %(job_location)s, %(salary_period)s, 
        #         %(min_salary)s, %(max_salary)s, %(edu_level)s, %(work_experience)s, %(skills)s, 
        #         %(travel)s, %(management)s, %(remote)s, %(job_source)s, {tw_date}
        #     )
        # """

        # # Execute the bulk insert
        # cursor.executemany(insert_temp_query, all_jd_list)
        # db_mysql_conn.commit()

        for one_jd in all_jd_list:
            try:
                insert_job_query = """
                    INSERT INTO temp_job (job_title, job_code, company_name, job_location, salary_period, 
                                min_salary, max_salary, edu_level, work_experience, skills, 
                                travel, management, remote, job_source, create_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                cursor.execute(insert_job_query, (
                    one_jd['job_title'], one_jd['job_code'], one_jd['company_name'], one_jd['job_location'],one_jd['salary_period'], 
                    one_jd['min_salary'], one_jd['max_salary'], one_jd['edu_level'],one_jd['work_experience'], one_jd['skills'], 
                    one_jd['travel'], one_jd['management'], one_jd['remote'], one_jd['job_source'], tw_date
                ))
                db_mysql_conn.commit()

                cats_for_one_jd = []
                job_code = one_jd['job_code']
                categories = one_jd['category']
                for category in categories:
                    cats_for_one_jd.append((job_code, category))

                for cat in cats_for_one_jd:
                    insert_jobcat_query = """
                        INSERT INTO temp_job_category (job_code, job_category) 
                        VALUES (%s, %s)
                    """
                    cursor.execute(insert_jobcat_query, (cat))
                db_mysql_conn.commit()

                # print("inserted jd, job_code: ", one_jd['job_code'])
            except Exception as e:
                logging.error(f"insert jd error, {e}")
                # db_conn.rollback()

        logger.info("job_temp inserted")
        logger.info("temp_jobcat table inserted")

        # check if the temporary table is empty
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM temp_job")
        result = cursor.fetchone()
        if result['cnt'] == 0:
            logger.error("No data in temp_job table.")
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
            WHERE job_source LIKE '%%hk.jobsdb.com%%'
            AND job_code NOT IN ({})
        """.format(', '.join(['%s'] * len(temp_job_codes)))

        cursor.execute(sql_delete, temp_job_codes)
        cursor.execute("COMMIT")
        logger.info("job removed deleted and updated")

        logger.info("jd_data updated and cleaned.")
        db_mysql_conn.close()
    except Exception as e:
        logger.error(f"Error updating data table: {e}")
        db_mysql_conn.rollback()

def crawler_jobsdb():
    try:
        all_codes = get_all_codes()
        logger.info(f"got all job codes:{len(all_codes)}")

        all_jd = get_all_jd(all_codes)
        logger.info(f"got all raw jd:{len(all_jd)}")
        all_raw_jd = raw_jd_to_json(all_jd)
        upload_to_s3(all_raw_jd)
        logger.info("uploaded all raw_jd")

        all_ok_jd = process_all_jd(all_jd)
        logger.info(len(all_ok_jd))
        logger.info(f"got all processed jd: {len(all_ok_jd)}")
        logger.info(all_ok_jd)
        insert_sql(all_ok_jd)
        logger.info(f"inserted all processed jd: {len(all_ok_jd)}")

        all_processed_jd = processed_jd_to_json(all_ok_jd)
        upload_to_s3(all_processed_jd)
        logger.info("uploaded processed_jd")

        logger.info("Done")
    except Exception as e:
        logger.error(f"crawler bug: {e}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='crawler_jobsdb',
    schedule="0 17 * * *",  # Run the DAG daily at 17:00 UTC
    start_date=datetime.today(),
    default_args=default_args,
    catchup=False,
    tags=['crawler', 'jobsdb', 'daily']
    ) as dag:

    t1 = PythonOperator(
        task_id='jobsdb_crawler',
        python_callable=crawler_jobsdb,
        dag=dag
    )

    (t1)

