FROM python:3.10
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt && rm requirements.txt
COPY api /opt/api
WORKDIR /opt/
RUN ls
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]