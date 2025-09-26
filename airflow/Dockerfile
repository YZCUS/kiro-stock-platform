FROM apache/airflow:2.8.0

# Switch to root user
USER root

# Set working directory
WORKDIR /opt/airflow

# Install additional dependencies
COPY --chown=airflow:root requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt

# Copy DAGs and include files
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root include/ /opt/airflow/include/

# Set environment variables
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags

# Switch to airflow user
USER airflow