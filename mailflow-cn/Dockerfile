FROM python:3.12-slim
WORKDIR /app
COPY requirements-demo.txt .
RUN pip install --no-cache-dir -r requirements-demo.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8101
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8101"]
