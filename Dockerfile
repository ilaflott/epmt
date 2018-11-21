FROM python:2.7

COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY models /app/models
COPY wait-for-it.sh main.py settings.py /app/
COPY sample-output /app/sample-output
RUN groupadd -r app && useradd -r -g app app && chown -R app:app /app
USER app
CMD python main.py 
#ENV FLASK_APP=epmt.py
#CMD ["flask", "run", "--host", "0.0.0.0"]