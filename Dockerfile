FROM python:2.7

COPY requirements.txt /home/app/
WORKDIR /home/app
RUN pip install -r requirements.txt
COPY models /home/app/models
COPY sample-output /home/app/sample-output
COPY EPMT.ipynb wait-for-it.sh epmt.py settings.py /home/app/
RUN groupadd -r app && useradd -r -g app app && chown -R app:app /home/app
USER app
# configured to connect to host 'db' by default
CMD python epmt.py 
#ENV FLASK_APP=epmt.py
#CMD ["flask", "run", "--host", "0.0.0.0"]