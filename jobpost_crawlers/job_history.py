import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

db_mysql_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                        user=os.getenv("RDS_USER"),
                        password=os.getenv("RDS_PASSWORD"),
                        database=os.getenv("RDS_DB"),
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor)

cursor = db_mysql_conn.cursor()


insert_data = []

# get total post
total_post = cursor.execute(
"""
SELECT COUNT(DISTINCT(job.job_code)) AS all_jobs
FROM job
LEFT JOIN job_category ON job.job_code = job_category.job_code;
"""
)
total_post = (cursor.fetchall())[0]['all_jobs']
insert_data.append(total_post)

# get post for individual category
job_list = ['iOS工程師','Android工程師','前端工程師','後端工程師','全端工程師', \
'數據分析師','資料科學家','資料工程師','AI工程師','資料庫管理人員']

for job in job_list:
    cursor.execute(
    """
    SELECT COUNT(DISTINCT(job.job_code)) AS job_posts
    FROM job
    LEFT JOIN job_category ON job.job_code = job_category.job_code
    WHERE job_category = %s;
    """, 
    (job,)
    )
    data = (cursor.fetchall())[0]['job_posts']
    insert_data.append(data)

# get date for history data
tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
tw_date = tw_time.date()
insert_data.append(tw_date)

print(insert_data)
print(len(insert_data))

insert_query = \
"""
INSERT INTO job_post_change (total_post, ios, android, frontend, backend, 
                fullstack, data_analyst, data_scientist, data_engineer, ai_engineer, 
                db_admin, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_post = VALUES(total_post), 
                ios = VALUES(ios), 
                android = VALUES(android),
                frontend = VALUES(frontend), 
                backend = VALUES(backend), 
                fullstack = VALUES(fullstack),
                data_analyst = VALUES(data_analyst), 
                data_scientist = VALUES(data_scientist), 
                data_engineer = VALUES(data_engineer),
                ai_engineer = VALUES(ai_engineer),
                db_admin = VALUES(db_admin);
"""


cursor.execute(insert_query, (insert_data[0], insert_data[1], insert_data[2], insert_data[3], insert_data[4], \
                                insert_data[5], insert_data[6], insert_data[7], insert_data[8], insert_data[9], \
                                insert_data[10], insert_data[11]))
db_mysql_conn.commit()

db_mysql_conn.close()