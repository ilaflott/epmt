FROM python-epmt:latest

WORKDIR /home/app
COPY models /home/app/models
COPY epmt EPMT.ipynb wait-for-it.sh *py /home/app/
RUN python -m py_compile *.py models/*.py
# Default executable, using info debug level 
ENTRYPOINT ["./epmt", "-d"]
# When run without anything, print help
CMD ["-h"]
