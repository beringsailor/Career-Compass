from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

seven_days_ago = datetime.combine(datetime.today() - timedelta(7),
                                datetime.min.time())

default_args = {
  'owner': 'airflow',
  'depends_on_past': False,
  'start_date': seven_days_ago,
  'retries': 1,
  'retry_delay': timedelta(minutes=5),
}

dag = DAG('crawler_dag', default_args=default_args)

t1 = PythonOperator(
    task_id='crawler_518',
    bash_command='python3 /home/ubuntu/airflow/dags/python_files/crawler_518.py',
    env={'AIRFLOW_HOME': '${AIRFLOW_HOME}'},
    dag=dag
)
t1