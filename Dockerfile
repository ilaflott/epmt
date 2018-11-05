FROM python:3.6

WORKDIR /app

RUN pip install Flask flask-restful pony psycopg2

RUN groupadd -r app && useradd -r -g app app \
    && chown -R app:app /app

USER app

# Copy directory files to /app
ADD . /app

ENV FLASK_APP=epmt.py

CMD ["flask", "run", "--host", "0.0.0.0"]