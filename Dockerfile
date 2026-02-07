FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ENTRYPOINT để chạy python + tham số (main.py)
ENTRYPOINT ["python"]

# CMD mặc định nếu không truyền tham số
CMD ["main.py"]