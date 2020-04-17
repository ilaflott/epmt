
import json
from waitress import serve

from flask import Flask, request, send_from_directory

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_folder='epmtdocs/site/')

@app.route('/')  
def send_filert():
    return send_from_directory(app.static_folder, 'index_ui.html')

@app.route('/<apage>')  
def send_file(apage):
    return send_from_directory(app.static_folder, apage)


if __name__ == "__main__":
   #app.run() ##Replaced with below code to run it using waitress 
   serve(app, host='0.0.0.0', port=8000)