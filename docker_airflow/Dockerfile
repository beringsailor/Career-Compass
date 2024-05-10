# Use an official Python runtime as a parent image
FROM apache/airflow:2.9.0-python3.9

# Copy the requirements.txt file into the container at /home/ubuntu/airflow
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Switch to root to install system packages
# USER root

# Install Google Chrome
# RUN apt-get update && apt-get install -y wget gnupg2 \
#     && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#     && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
#     && apt-get update \
#     && apt-get install -y google-chrome-stable

# Switch back to the default user 'airflow'
USER airflow
