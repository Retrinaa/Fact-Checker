FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Worker service: runs the bot with long polling, no exposed port needed.
CMD ["python", "bot.py"]
