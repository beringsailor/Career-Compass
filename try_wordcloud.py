import os
import numpy as np
from PIL import Image
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
import pymysql
from pymysql import MySQLError
from dotenv import load_dotenv

load_dotenv() 

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

wc = WordCloud(width=800, height=400, background_color='white', max_words=200).generate(long_list)

# Display the word cloud
plt.imshow(wc, interpolation='bilinear')
plt.axis('off')
plt.show()