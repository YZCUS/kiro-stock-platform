FROM apache/airflow:2.8.0

# Set working directory
WORKDIR /opt/airflow

# Install additional dependencies
COPY --chown=airflow:root requirements.txt /requirements.txt
USER airflow
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt

# Copy the complete runtime; production does not bind-mount source code.
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root plugins/ /opt/airflow/plugins/
COPY --chown=airflow:root config/ /opt/airflow/config/

# Set environment variables
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
ENV PYTHONPATH=/opt/airflow
