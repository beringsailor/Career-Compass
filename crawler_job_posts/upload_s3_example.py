import boto3
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

load_dotenv()

def list_to_json(input_list):
    # get taiwan date when inserting
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    tw_date = tw_time.date()

    filename = f"jd_104_{tw_date}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(input_list, json_file, ensure_ascii=False, indent=4)

    return filename

# upload_s3
def upload_to_s3(filename, BUCKET_NAME):
    print(BUCKET_NAME)
    try:
        s3.upload_file(filename, BUCKET_NAME, filename)
    except Exception as e:
        return {"errors": str(e)}
    
# access s3 bucket location and save json daily
s3 = boto3.client("s3", 
    region_name=os.getenv("REGION_NAME"),
    aws_access_key_id=os.getenv("S3_KEY"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY"))
BUCKET_NAME = os.getenv("S3_BUCKET")

# with open(filename, "rb") as f:
#     # Upload the file object to the root directory of the S3 bucket
#     s3.upload_file(filename, BUCKET_NAME, filename)

def check_s3_connection():
    try:
        s3 = boto3.client("s3")
        response = s3.list_buckets()
        return True
    except Exception as e:
        # If there's any error, print the error and return False
        print("Error:", e)
        return False

# # Check S3 connection
# if check_s3_connection():
#     print("Connection to S3 is successful.")
# else:
#     print("Failed to connect to S3.")

# all_jds = [{'job_title': 'AI研發工程師', 'company_name': '區塊科技股份有限公司', 'job_location': '台北市', 'salary_info': '月薪50,000~75,000元', 'min_salary': 50000, 'max_salary': 75000, 'edu_level': '專科以上', 'work_experience': '1年以上', 'skills': 'Linux,Git,Java,Python', 'travel': '無需出差外派', 'management': '不需負擔管理責任', 'remote': '不可遠端工作', 'job_category': ['軟體工程 師', '全端工程師', '區塊鏈工程師']}]

# filename = list_to_json(all_jds)
# result = upload_to_s3(filename, BUCKET_NAME)

import pymysql
from pymysql import MySQLError

db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                                user=os.getenv("RDS_USER"),
                                password=os.getenv("RDS_PASSWORD"),
                                database=os.getenv("RDS_DB"),
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)

cursor = db_mysql_conn.cursor()

skills = cursor.execute(
        """
        SELECT skills
        FROM aws_pp.job
        WHERE skills IS NOT NULL;
        """
    )
skills = cursor.fetchall()

skill_list = []
for skill in skills:
    skill_list.append(skill['skills'])

comma_separated = ','.join(skill_list)
long_list = ' '.join(comma_separated.split(','))
print(long_list)