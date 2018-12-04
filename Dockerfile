FROM python:2.7

COPY requirements.txt /home/app/
WORKDIR /home/app
RUN pip install -r requirements.txt
COPY models /home/app/models
COPY sample-data /home/app/sample-data
COPY EPMT.ipynb wait-for-it.sh main.py experiment.py settings.py settings_pg.py /home/app/
RUN groupadd -r app && useradd -r -g app app && chown -R app:app /home/app
USER app
# configured to connect to host 'db' by default
CMD python experiment.py && python main.py
