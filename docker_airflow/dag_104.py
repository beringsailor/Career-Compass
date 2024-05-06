import time
import random
import requests
import unicodedata
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from logging.handlers import TimedRotatingFileHandler

from airflow import DAG
from crawler_104 import crawl_id_all_pages
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python import PythonOperator

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

# to prevent ERROR:cert_issuer_source_aia.cc(35)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
# blockchain SWE
driver.get("https://www.104.com.tw/jobs/search/?jobcat=2007001023")


dag = DAG(
    dag_id = '104_to_aws',
    start_date = datetime.today(),
    schedule_interval  = None,
    tags = ['appworks'],
)

run_script_task = PythonOperator(
    task_id='run_my_script',
    python_callable=crawl_id_all_pages,
)

# def transform_read_s3(**kwargs):

#     s3 = S3Hook(aws_conn_id='aws_default')
#     bucket = 'careercompass'
#     key = 'jd_104_2024-04-16.json'
#     file_obj = s3.get_key(key, bucket_name=bucket)
#     file_content = file_obj.get()['Body'].read().decode('utf-8')
#     print(file_content)

# transform_read_s3()

run_script_task