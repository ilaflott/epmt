#!/usr/bin/env python
from waitress import serve

from flask import Flask, send_from_directory

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_folder='epmtdocs/site/')

# Handle the case where user visits the root of static server
# This is needed as we aren't using index.html files in directories
@app.route('/')
def send_filert():
    return send_from_directory(app.static_folder, 'README.html')

# Serve any requested page from within the site directory
@app.route('/<apage>')
def send_file(apage):
    return send_from_directory(app.static_folder, apage)


if __name__ == "__main__":
    # app.run() ## Replaced with below code to run it using waitress
    serve(app, host='0.0.0.0', port=8000)
