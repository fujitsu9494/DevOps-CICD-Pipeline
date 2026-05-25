FROM python:3.11

WORKDIR /app

# install dependencies first (better caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copy app source
COPY . /app

EXPOSE 5000

CMD ["python", "flask_app.py"]