import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
# see https://community.plot.ly/t/nolayoutexception-on-deployment-of-multi-page-dash-app-example-code/12463/2?u=dcomfort
from .app import app
from .layouts import *
from .callbacks import *


def init_app():
    # see https://dash.plot.ly/external-resources to alter header, footer and favicon
    app.index_string = ''' 
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>EPMT Job Display</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    #<img src="\\assets\\cc_logo.jpeg" width="120" height="120">
    
    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ])

# Update page
# # # # # # # # #

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname'),
              Input('url', 'href')])
def display_page(pathname,pfullurl):
    from .app import fullurl
    app.fullurl = pfullurl
    if pathname == '' or pathname == '/':
        return recent_jobs_page
    elif pathname == '/unprocessed/':
        return layout_unprocessed
    elif pathname == '/alerts/':
        return layout_alerts
    elif pathname == '/refs/':
        return layout_references
    elif pathname == '/table/':
        return layouts(pfullurl)
    else:
        return noPage

# # # # # # # # #
# detail the way that external_css and external_js work and link to alternative method locally hosted
# # # # # # # # #
#external_css = ["https://cdnjs.cloudflare.com/ajax/libs/normalize/7.0.0/normalize.min.css",
#                "https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
#                "https://fonts.googleapis.com/css?family=Raleway:400,300,600",
#                "https://codepen.io/bcd/pen/KQrXdb.css",
#                "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
#                ]#"https://codepen.io/dmcomfort/pen/JzdzEZ.css"]


#for css in external_css:
    #app.css.append_css({"external_url": css})

#external_js = ["https://code.jquery.com/jquery-3.2.1.min.js",
#               "https://codepen.io/bcd/pen/YaXojL.js"]

#for js in external_js:
#    app.scripts.append_script({"external_url": js})

if __name__ == '__main__':
    init_app()
    app.run_server(debug=True, host='0.0.0.0')
