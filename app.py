# -*- coding: utf-8 -*-
# for line 341

import flask
import os
import re
import jwt
import logging
import pymysql
from datetime import datetime, timedelta, UTC
import matplotlib.pyplot as plt
from io import BytesIO
from hashlib import sha256
from dotenv import load_dotenv
from functools import wraps
from wordcloud import WordCloud
from flask import session, request, render_template, send_file, jsonify, make_response, flash, redirect, url_for
# from werkzeug.middleware.dispatcher import DispatcherMiddleware

load_dotenv()

server = flask.Flask(__name__)
server.secret_key = os.getenv("SECRET_KEY")
server.json.ensure_ascii = False

# get jwt token info
SECRET = os.getenv("SECRET")
ALGORITHM = os.getenv("ALGORITHM")

# Connect to AWS RDS
def connect_db():
    db_conn = pymysql.connect(host=os.getenv("RDS_HOST"),
                            user=os.getenv("RDS_USER"),
                            password=os.getenv("RDS_PASSWORD"),
                            database=os.getenv("RDS_DB"),
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    return db_conn

conn = connect_db()
cursor = conn.cursor()

# get jwt token info
SECRET = os.getenv("SECRET")
ALGORITHM = os.getenv("ALGORITHM")

def login_required(view_func):
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        access_token = request.cookies.get('access_token')
        if access_token:
            try:
                payload = jwt.decode(access_token.split(' ')[1], SECRET, algorithms=[ALGORITHM])
                user_id = payload.get('user_id')
                if user_id:
                    return view_func(user_id, *args, **kwargs)  # Pass user_id if logged in
            except jwt.ExpiredSignatureError:
                flash('Session Timeout. Please log in again.', 'error')
            except (jwt.InvalidTokenError, jwt.DecodeError):
                flash('Invalid token. Please log in again.', 'error')

        # If not logged in or token is invalid, proceed without user_id
        return view_func(None, *args, **kwargs)

    return decorated_function

@server.route('/', methods=['GET','POST'])
@login_required
def homepage(user_id=None):
    conn = connect_db()
    cursor = conn.cursor()
    # Example of different content based on login status
    if user_id:
        account = cursor.execute('SELECT name FROM user WHERE id=%s', user_id)
        account = cursor.fetchall()
        name = account[0]['name']

        bookmarked = cursor.execute('SELECT * FROM user_bookmark WHERE user_id = %s', (user_id,))
        bookmarked = cursor.fetchall()
        bookmarked_list = []
        for b in bookmarked:
            bookmarked_list.append(b['job_code'])
    else:
        name=None
        bookmarked_list=None
        
    query = "SELECT job_title, company_name, job_location, salary_period, job_source, job_code \
                FROM job WHERE 1=1 ORDER BY RAND() LIMIT 5;"
    cursor.execute(query)
    recommends = cursor.fetchall()
    conn.close()

    return render_template('homepage.html', recommends=recommends, name=name, user_id=user_id)

@server.route('/job/search', methods=['GET'])
@login_required
def search_jobs_get(user_id=None):
    try:
        job_title = request.args.get('job_title')
        salary = request.args.get('salary')
        location = request.args.get('location')
        page = request.args.get('page', default=1, type=int)

        conn = connect_db()
        cursor = conn.cursor()
        if user_id:
            account = cursor.execute('SELECT name FROM user WHERE id=%s', user_id)
            account = cursor.fetchall()
            name = account[0]['name']

            bookmarked = cursor.execute('SELECT * FROM user_bookmark WHERE user_id = %s', (user_id,))
            bookmarked = cursor.fetchall()
            bookmarked_list = []
            for b in bookmarked:
                bookmarked_list.append(b['job_code'])
        else:
            name = None
            bookmarked_list = None
        
        query = "SELECT job_title, company_name, job_location, salary_period, job_source, job_code FROM job WHERE 1=1"
        params = []

        if job_title:
            query += " AND job_title LIKE %s"
            params.append('%' + job_title + '%')
        if salary:
            query += " AND min_salary > %s"
            params.append(salary)
        if location:
            query += " AND job_location LIKE %s"
            params.append('%' + location + '%')

        # Calculate the offset based on the page number and number of results per page
        per_page = 10
        offset = (page - 1) * per_page

        # Modify the query to include pagination
        query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        cursor.execute(query, params)
        results = cursor.fetchall()

        if results == None:
            word = "no more jobs"
            return render_template('homepage.html', name=name, page=page, \
                                    job_title=job_title, salary=salary, location=location, \
                                    bookmarked_list=bookmarked_list, user_id=user_id)

        conn.close()
        
        # Render template with search results
        return render_template('homepage.html', name=name, results=results, page=page, \
                                    job_title=job_title, salary=salary, location=location, \
                                    bookmarked_list=bookmarked_list, user_id=user_id)
    except Exception as e:
        logging.error(f"Error in job search GET request: {e}")

@server.route('/bookmark/<user_id>/<job_code>', methods=['GET'])
@login_required
def check_bookmark(uid_decorator, user_id, job_code):
    conn = connect_db()
    cursor = conn.cursor()
    if user_id:
        # Check if the post is already in the favorite list
        cursor.execute('SELECT * FROM user_bookmark WHERE job_code=%s AND user_id=%s', (job_code,user_id,))
        post_in_list = cursor.fetchall()

        if post_in_list:
            # If the post is already in the list, remove it
            cursor.execute('DELETE FROM user_bookmark WHERE job_code=%s AND user_id=%s', (job_code,user_id,))
            action = 'remove'
        else:
            # If the post is not in the list, add it
            cursor.execute('INSERT INTO user_bookmark (job_code, user_id) VALUES (%s, %s)', (job_code,user_id,))
            action = 'add'
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'action': action})

# need to add return results for recommended jobs
@server.route('/job/<job_code>', methods=['GET'])
@login_required
def get_jd(user_id, job_code):
    conn = connect_db()
    cursor = conn.cursor()
    
    if user_id:
        account = cursor.execute('SELECT name FROM user WHERE id=%s', user_id)
        account = cursor.fetchall()
        name = account[0]['name']

        bookmarked = cursor.execute('SELECT * FROM user_bookmark WHERE user_id = %s', (user_id,))
        bookmarked = cursor.fetchall()
        bookmarked_list = []
        for b in bookmarked:
            bookmarked_list.append(b['job_code'])
    else:
        name = None
        bookmarked_list = None
    
    if job_code:
        results = cursor.execute("SELECT * FROM job WHERE job_code=%s", (job_code,))
        results = cursor.fetchall()

        cursor.execute("""
            SELECT DISTINCT job.job_code AS job_code, job_title, company_name, job_location
            FROM job_category
            JOIN job ON job_category.job_code = job.job_code 
            WHERE job_category IN (
                SELECT job_category
                FROM job_category
                WHERE job_code=%s)
            AND job.job_code != %s
            LIMIT 2
            """, (job_code, job_code,))
        sides = cursor.fetchall()

        conn.close()

    return render_template('job_content.html', results=results, user_id=user_id, \
                           sides=sides, name=name, bookmarked_list=bookmarked_list)

@server.route('/user/login', methods=['GET'])
def get_login_page():
    return render_template('login.html')

@server.route('/api/user/signup', methods=['POST']) 
def signup():
    if request.method == 'POST':
        email = request.form['email']
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message_signup = "Invalid email format"
            return render_template('login.html', message_signup=message_signup)
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            try:
                name = request.form['name']
                email = request.form['email']
                # hash pwd, email
                password = request.form['password']
                hashed_pw = sha256(password.encode('utf-8')).hexdigest()

                mail_exist = cursor.execute('SELECT * FROM user WHERE email=%s', email)
                if mail_exist:
                    message_signup = "email account already exists!"
                    return render_template('login.html', message_signup=message_signup)
                else:
                    cursor.execute('INSERT INTO user (name, email, password) \
                                    VALUES (%s, %s, %s)', (name, email, hashed_pw))
                    lastrowid = cursor.lastrowid
                    response = cursor.execute('SELECT id, name, email \
                                              FROM user WHERE id=%s', lastrowid)
                    response = cursor.fetchall()
                    conn.commit()
                
                payload = {
                    'user_id': lastrowid,
                    'exp' : datetime.now(UTC) + timedelta(seconds=3600)
                    }
                token = jwt.encode(payload, SECRET, ALGORITHM)

                resp = make_response(redirect(url_for('homepage')))

                token_bearer = 'Bearer' + ' ' + str(token)
                resp.set_cookie('access_token', token_bearer)
                return resp
            except Exception as e:
                logging.error("signup error")

        cursor.close()
        conn.close()

@server.route('/api/user/signin', methods=['POST']) 
def signin():
    if request.method == 'POST':
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            try:
                email = request.form['email']
                password = request.form['password']
                hashed_pw = sha256(password.encode('utf-8')).hexdigest()
                values = (email, hashed_pw)

                account = cursor.execute('SELECT id, name, email \
                                    FROM user WHERE email=%s AND password=%s', values)
                account = cursor.fetchall()
                if not account:
                    flash('Invalid email or password for signing in', 'signin_error')
                    message_signin = "Wrong email or password"
                    return render_template('login.html', message_signin=message_signin)
                
                payload = {
                    'user_id':account[0]['id'],
                    'exp' : datetime.now(UTC) + timedelta(seconds=3600)
                    }
                token = jwt.encode(payload, SECRET, ALGORITHM)

                resp = make_response(redirect(url_for('homepage')))

                token_bearer = 'Bearer' + ' ' + str(token)
                resp.set_cookie('access_token', token_bearer)
                return resp
            except Exception as e:
                logging.error("signin error")
            finally:
                cursor.close()
                conn.close()

@server.route('/user/profile', methods=['GET']) 
@login_required
def profile(user_id):
    if user_id:
        try:
            conn = connect_db()
            cursor = conn.cursor()
            account = cursor.execute("""
                    SELECT job.job_code as job_code, user.id AS user_id, name , email, job_source,
                    job_title, company_name AS company, job_location AS location
                    FROM pp_aws.user
                    LEFT JOIN user_bookmark ON user.id = user_bookmark.user_id
                    LEFT JOIN job ON user_bookmark.job_code = job.job_code
                    WHERE user.id=%s LIMIT 5
                    """, user_id)
            account = cursor.fetchall()
            data = account
            name = account[0]['name']
            return render_template('profile.html', data=data, name=name)
        except Exception as e:
            logging.error("user profile api error")

@server.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard(user_id=None):
    conn = connect_db()
    cursor = conn.cursor()

    name = None
    # Example of different content based on login status
    if user_id:
        query = "SELECT job_title, company_name, job_location, salary_period, job_source, job_code \
                    FROM job WHERE 1=1 ORDER BY RAND() LIMIT 10;"
        cursor.execute(query)
        recommends = cursor.fetchall()

        account = cursor.execute('SELECT name FROM user WHERE id=%s', user_id)
        account = cursor.fetchall()
        name = account[0]['name']

        conn.close()
    return render_template('dashboard.html', name=name)

@server.route('/api/dashboard/job_vacancy', methods=['POST'])
def get_vacancy_ratio():
    if request.method == 'POST':
        keyword = request.json.get('input_text') if request.json else None

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if keyword:
            keyword_mappings = {
                'iOS工程師': 'ios',
                'Android工程師': 'android',
                '前端工程師': 'frontend',
                '後端工程師': 'backend',
                '全端工程師': 'fullstack',
                '數據分析師': 'data_analyst',
                '資料科學家': 'data_scientist',
                '資料工程師': 'data_engineer',
                'AI工程師': 'ai_engineer',
                '資料庫管理人員': 'db_admin'
            }

            query_keyword = keyword_mappings.get(keyword, keyword)

            job_posts = cursor.execute(
            """
            SELECT total_post - {keyword} AS others, {keyword} AS chose_cat, date
            FROM job_post_change
            ORDER BY date DESC
            LIMIT 7;
            """.format(keyword=query_keyword)
            )
        else:
            job_posts = cursor.execute(
            """
            SELECT total_post - total_post AS others, total_post AS chose_cat, date
            FROM job_post_change
            ORDER BY date DESC
            LIMIT 7;
            """
            )

        job_posts = cursor.fetchall()
        conn.close()

        others = []
        chose_cat = []
        dates = []

        for day_post in job_posts:
            others.append(day_post['others'])
            chose_cat.append(day_post['chose_cat'])
            date = day_post['date'].strftime('%Y-%m-%d')
            dates.append(date)
            
        return jsonify({'others': others, 'chose_cat': chose_cat, 'dates': dates})
    
    except Exception as e:
        logging.warning("An error occurred:", e) 

@server.route('/api/dashboard/job_salary')
def get_categories():
    try:
        conn = connect_db()
        cursor = conn.cursor()

        category_avgs = cursor.execute(
            """
            SELECT job_category, ROUND(AVG(avg_salary_per_job), 0) AS category_average
            FROM (
                SELECT (min_salary + max_salary) / 2 AS avg_salary_per_job, job_location, min_salary, max_salary, salary_period, job_category
                FROM job
                LEFT JOIN job_category ON job.job_code = job_category.job_code
                WHERE job_category IN (
                    'iOS工程師','Android工程師','前端工程師','後端工程師','全端工程師',
                    '數據分析師','資料科學家','資料工程師','AI工程師','資料庫管理人員')
                    AND (min_salary != 0 OR max_salary != 0) 
                    AND max_salary != 9999999 
                    AND salary_period != '待遇面議' 
                    AND NOT (salary_period LIKE '年薪%%' OR salary_period LIKE '時薪%%')
                    AND LEFT(job_location, 3) IN (
                        '連江縣','台北市','新北市','桃園市','台中市',
                        '台南市', '高雄市','宜蘭縣','新竹縣','苗栗縣',
                        '彰化縣', '南投縣','雲林縣','嘉義縣','屏東縣',
                        '花蓮縣', '台東縣','澎湖縣','基隆市','新竹市',
                        '嘉義市')
            ) AS subquery_alias
            GROUP BY job_category
            ORDER BY category_average DESC;
            """
            )
        
        category_avgs = cursor.fetchall()
        conn.close()

        category = []
        category_avg = []
        for item in category_avgs:
            category.append(item['job_category'])
            category_avg.append(int(item['category_average']))

        return jsonify({'category': category, 'category_average': category_avg})
    
    except Exception as e:
        logging.error("Dashboard job_salary error") 

@server.route('/api/dashboard/region_salary', methods=['POST'])
def display_region_salary():
    if request.method == 'POST':
        keyword = request.json.get('input_text') if request.json else None

    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        if keyword:
            salary_avgs = cursor.execute(
            """
            SELECT LEFT(job_location, 3) AS region, ROUND(AVG(avg_salary_per_job), 0) AS region_average
            FROM (
                SELECT (min_salary + max_salary) / 2 AS avg_salary_per_job, job_location, min_salary, max_salary, salary_period, job_category
                FROM job
                LEFT JOIN job_category on job.job_code = job_category.job_code
                WHERE (min_salary != 0 OR max_salary != 0) 
                    AND max_salary != 9999999 
                    AND salary_period != '待遇面議' 
                    AND NOT (salary_period LIKE '年薪%%' OR salary_period LIKE '時薪%%')
                    AND LEFT(job_location, 3) IN (
                        '連江縣','台北市','新北市','桃園市','台中市',
                        '台南市', '高雄市','宜蘭縣','新竹縣','苗栗縣',
                        '彰化縣', '南投縣','雲林縣','嘉義縣','屏東縣',
                        '花蓮縣', '台東縣','澎湖縣','基隆市','新竹市',
                        '嘉義市')
            ) AS subquery_alias
            WHERE job_category = %s
            GROUP BY LEFT(job_location, 3)
            ORDER BY region_average DESC;
            """,
            (keyword,)
            )
        else:
            salary_avgs = cursor.execute(
            """
            SELECT LEFT(job_location, 3) AS region, ROUND(AVG(avg_salary_per_job), 0) AS region_average
            FROM (
                SELECT (min_salary + max_salary) / 2 AS avg_salary_per_job, job_location, min_salary, max_salary, salary_period, job_category
                FROM job
                LEFT JOIN job_category on job.job_code = job_category.job_code
                WHERE (min_salary != 0 OR max_salary != 0) 
                    AND max_salary != 9999999 
                    AND salary_period != '待遇面議' 
                    AND NOT (salary_period LIKE '年薪%%' OR salary_period LIKE '時薪%%')
                    AND LEFT(job_location, 3) IN (
                        '連江縣','台北市','新北市','桃園市','台中市',
                        '台南市', '高雄市','宜蘭縣','新竹縣','苗栗縣',
                        '彰化縣', '南投縣','雲林縣','嘉義縣','屏東縣',
                        '花蓮縣', '台東縣','澎湖縣','基隆市','新竹市',
                        '嘉義市')
            ) AS subquery_alias
            GROUP BY LEFT(job_location, 3)
            ORDER BY region_average DESC;
            """
            )

        salary_avgs = cursor.fetchall()
        conn.close()

        region = []
        region_avg = []
        for item in salary_avgs:
            # adjust teh space between axis and graph
            region.append(item['region']+ ' ')
            region_avg.append(int(item['region_average']))

        return jsonify({'region': region, 'region_average': region_avg})
    
    except Exception as e:
        logging.error("Dashboard region_salary error") 

@server.route('/api/dashboard/edu_level', methods=['POST'])
def display_edu_level():
    if request.method == 'POST':
        keyword = request.json.get('input_text') if request.json else None

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if keyword:
            edu_types = cursor.execute(
            """
            SELECT LEFT(edu_level, 2) AS min_edu_level, COUNT(*) AS count
            FROM job
            LEFT JOIN job_category on job.job_code = job_category.job_code
            WHERE job_category = %s
            AND edu_level IS NOT NULL
            AND LEFT(edu_level, 2) IN ('不拘','高中','專科','大學','碩士','博士')
            GROUP BY min_edu_level;
            """,
            (keyword,)
            )
        else:
            edu_types = cursor.execute(
            """
            SELECT LEFT(edu_level, 2) AS min_edu_level, COUNT(*) AS count
            FROM job
            WHERE edu_level IS NOT NULL
            AND LEFT(edu_level, 2) IN ('不拘','高中','專科','大學','碩士','博士')
            GROUP BY min_edu_level;

            """
            )

        edu_types = cursor.fetchall()
        conn.close()

        edu_name = []
        edu_name_num = []
        for edu_type in edu_types:
            edu_name.append(edu_type['min_edu_level'])
            edu_name_num.append(edu_type['count'])

        labels = edu_name
        values = edu_name_num

        return jsonify({'values': values, 'labels': labels})
    
    except Exception as e:
        logging.warning("An error occurred:", e) 

@server.route('/api/dashboard/generate_wordcloud', methods=['POST'])
def display_wordcloud():
    if request.method == 'POST':
        keyword = request.json.get('input_text') if request.json else None

    try:
        conn = connect_db()
        cursor = conn.cursor()

        if keyword:
            skills = cursor.execute(
                """
                SELECT *
                FROM job
                LEFT JOIN job_category on job.job_code = job_category.job_code
                WHERE skills IS NOT NULL
                AND job_category = %s
                # ORDER BY RAND()
                # LIMIT 1000;
                """,
                (keyword,)
            )
        else: 
            skills = cursor.execute(
                """
                SELECT *
                FROM job
                WHERE skills IS NOT NULL
                # ORDER BY RAND()
                # LIMIT 1000;
                """
            )
        
        skills = cursor.fetchall()
        conn.close() 

        skill_list = []
        for skill in skills:
            skill_list.append(skill['skills'])

        comma_separated = ','.join(skill_list)
        input_text = ' '.join(comma_separated.split(','))

        # Generate word cloud
        wc = WordCloud(collocations=False, width=800, height=400, background_color='white', max_words=400).generate(input_text)
        
        # Save the word cloud to a BytesIO object
        img = BytesIO()
        wc.to_image().save(img, format='PNG')
        img.seek(0)
        
        return send_file(img, mimetype='image/png')
    except Exception as e:
        logging.warning("An error occurred:", e) 

if __name__ == '__main__':
    server.run(debug=True, host='127.0.0.1', port=5000)