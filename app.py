import flask
import dash
import os
import pymysql
from flask import render_template, request
from dotenv import load_dotenv

server = flask.Flask(__name__)
# app = dash.Dash(__name__, server=server)

load_dotenv()
# connect to database
db_mysql_conn = pymysql.connect(host=os.getenv("MYSQL_HOST"),
                                user=os.getenv("MYSQL_USER"),
                                password=os.getenv("MYSQL_PASSWORD"),
                                database=os.getenv("MYSQL_DB"),
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)
cursor = db_mysql_conn.cursor()


@server.route('/', methods=['GET', 'POST'])
def homepage():
    return render_template('homepage.html')

@server.route('/search', methods=['POST'])
def search_jobs():
    if request.method == 'POST':
        
        job_title = request.form['job_title']
        salary = request.form['salary']
        location = request.form['location']

        if job_title or salary or location:
            db_mysql_conn
            cursor = db_mysql_conn.cursor()

            query = "SELECT job_title, company_name, job_location, salary_period, job_source FROM pp_test.job WHERE 1=1"
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

            cursor.execute(query, params)
            results = cursor.fetchall()
        
        else:
            db_mysql_conn
            cursor = db_mysql_conn.cursor()

            cursor.execute("SELECT job_title, company_name, job_location, salary_period, job_source FROM pp_test.job")
            results = cursor.fetchall()

        return render_template('homepage.html', results=results)

    return render_template('homepage.html')

if __name__ == '__main__':
    server.run(debug=True)