FROM apache/airflow:2.8.0

# Install additional dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy DAGs and include files
COPY dags/ /opt/airflow/dags/
COPY include/ /opt/airflow/include/

# Set environment variables
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags

USER airflow