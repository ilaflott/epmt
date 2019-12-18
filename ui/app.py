import dash
import dash_bootstrap_components as dbc
# Import epmt parent folder
#import sys
#sys.path.append("./..")
from logging import getLogger
#from epmtlib import set_logging
logger = getLogger(__name__)  # you can use other name
#set_logging(intlvl=3, check=False)
logger.propagate = False


def resource_path(relative_path):
    import sys
    import os
    # get absolute path to resource
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# print(resource_path("ui/assets"))

external_stylesheets = [ # Remote Styles
                        dbc.themes.BOOTSTRAP,
                        "https://cdnjs.cloudflare.com/ajax/libs/normalize/7.0.0/normalize.min.css",
                        "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",

                         # Fonts
                        "https://fonts.googleapis.com/css?family=Raleway:400,300,600",
                        "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",

                        # Locally saved /assets/*
                        #"https://codepen.io/bcd/pen/KQrXdb.css", # Bordering & Theming
                        #"https://codepen.io/dmcomfort/pen/JzdzEZ.css", # Data table theming
                        #'https://codepen.io/chriddyp/pen/bWLwgP.css', # Plotly Css
                        ]

# assets folder recipe:
# https://stackoverflow.com/questions/55596932/how-can-i-include-assets-of-a-dash-app-into-an-exe-file-created-with-pyinstaller
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, url_base_pathname='/', assets_folder=resource_path('ui/assets'))
server = app.server
app.config.suppress_callback_exceptions = True
fullurl = ''
#app.css.config.serve_locally = False
#app.scripts.config.serve_locally = False

# import dash_auth

# VALID_USERNAME_PASSWORD_PAIRS = [
#     ['alg', 'mexicovacation']
# ]

# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )
