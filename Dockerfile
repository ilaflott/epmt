FROM python:2.7

COPY requirements.txt /home/app/
WORKDIR /home/app
RUN pip install -r requirements.txt
COPY models /home/app/models
# COPY sample-data /home/app/sample-data
COPY epmt EPMT.ipynb wait-for-it.sh *py /home/app/
RUN python -m py_compile *.py models/*.py			# Compile everything
RUN groupadd -r app && useradd -r -g app app && chown -R app:app /home/app
USER app
# Default executable, using info debug level 
ENTRYPOINT ["./epmt", "-d"]
# When run without anything, print help
CMD ["-h"]
