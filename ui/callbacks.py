from .components import convtounit, get_unit, power_labels
from .layouts import dcc, DEFAULT_ROWS_PER_PAGE
import dash
from dash.dependencies import Input, Output, State
from .app import app
import plotly.graph_objs as go
from plotly import tools
from datetime import datetime as dt
from datetime import date, timedelta
import io
from datetime import datetime
import numpy as np
import pandas as pd

from logging import getLogger
import epmt_settings as settings

# do NOT do any epmt imports until logging is set up
# using set_logging, other than import set_logging
# from epmtlib import set_logging
logger = getLogger(__name__)  # you can use other name
# set_logging(settings.verbose if hasattr(settings, 'verbose') else 0, check=True)



# pd.options.mode.chained_assignment = None
import ui.refs as refs
#import jobs

@app.callback(dash.dependencies.Output('content', 'data'),
              [dash.dependencies.Input('test', 'children')])
def display_page(pathname):
    logger.debug("Pathname is {}".format(pathname))
    from .jobs import job_gen
    joblist = job_gen().df
    df = joblist.df
    return df.to_dict('records')


@app.callback(
    dash.dependencies.Output('placeholderedit', 'children'),
    [dash.dependencies.Input('edit-Model-save-btn', 'n_clicks_timestamp')],
    [dash.dependencies.State('edit-model-jobs-drdn', 'value'),
     dash.dependencies.State('table-ref-models', 'data'),
     dash.dependencies.State('table-ref-models', 'selected_rows')]
)
def test_job_update(saveclick, sel_jobs, ref_data, sel_ref):
    if sel_ref and len(sel_ref) > 0:
        from .components import recent_button
        recentbtn = recent_button({'save_model': saveclick})
        if recentbtn == 'save_model':
            from json import dumps
            # Get Dropdown Selected
            logger.debug(
                "Test side callback sel jobs {} selected ref {}".format(sel_jobs, sel_ref))
            selected_refs = ref_data[sel_ref[0]]
            logger.debug("Model:{} Jobs:{}".format(
                selected_refs['name'], sel_jobs))
            # Update DF with new Jobs
            refs.ref_df.loc[(refs.ref_df.name == selected_refs['name']), 'jobs'] = dumps(
                sel_jobs)
            return ""  # return placeholder dataframe has been updated


@app.callback(
    dash.dependencies.Output('name-model-div', 'style'),
    [dash.dependencies.Input('create-newModel-btn', 'n_clicks_timestamp'),
    dash.dependencies.Input('create-Model-close-btn', 'n_clicks_timestamp')]
)
def open_create_model_div(create_model_btn, close_model_btn):
    from .components import recent_button
    recentbtn = recent_button({'create_model_open_div': create_model_btn,
    'close':close_model_btn})
    if recentbtn == 'create_model_open_div':
        return {'display': 'contents'}
    elif recentbtn == 'close':
        return {'display': 'none'}
    else:
        return {'display': 'none'}

# Output
#       alert dialog(style,text,visability) (select jobs, analysis running, no model found)
# Input
#       Run Analysis button
# State
#       selected jobs
@app.callback(
    [
        dash.dependencies.Output('run-create-alert', 'children'),
        dash.dependencies.Output('run-create-alert', 'is_open')
    ],
    [
        dash.dependencies.Input('run-analysis-btn', 'n_clicks_timestamp'),
    ],
    [
        dash.dependencies.State('table-multicol-sorting', 'selected_rows'),
        dash.dependencies.State('table-multicol-sorting', 'data'),
        dash.dependencies.State('model-selector-dropdown', 'value')
    ])
def run_analysis(run_analysis_btn, sel_jobs, job_data, selected_model):
    from .components import recent_button
    recentbtn = recent_button({'run_analysis': run_analysis_btn})
    if recentbtn is 'run_analysis':
        if sel_jobs:
            #selected_rows = [str(job_data[i]['job id']) for i in sel_jobs]
            selected_rows = [(str(job_data[i]['job id']),job_data[i]['exp_name'],job_data[i]['exp_component']) for i in sel_jobs]
            logger.info(
                "Find reference models for each job\nJobs:{}".format([j[0] for j in selected_rows]))
            # Check for matching models
            model_tags = {'exp_name':selected_rows[0][1], 'exp_component':selected_rows[0][2]}
            from json import dumps
            model_tags = dumps(model_tags)
            import ui.refs as refs
            ref_df = refs.ref_df
            for model in ref_df.to_dict('records'):
                if model['tags'] == model_tags:
                    logger.debug("Found a matching model {}".format(model))
            # Detect outliers/Run analysis
            #from jobs import detect_outlier_jobs
            from epmt_outliers import detect_outlier_jobs
            from epmt_query import get_refmodels
            logger.debug("Model Selected is {}".format(selected_model))
            if selected_model == 'None':
                hackmodel = None
            else:
                hackmodel = get_refmodels(name=selected_model)[0]['id']
            try:
                analysis = detect_outlier_jobs([j[0] for j in selected_rows], trained_model=hackmodel)
                analysis_simplified = "Duration Outliers: " + str(analysis[1]['duration'][1]) +\
                " CPU Time Outliers: " + str(analysis[1]['cpu_time'][1]) +\
                " Number of Processes Outliers: " + str(analysis[1]['num_procs'][1])
                if analysis:
                    logger.debug("Analysis returned \n{}".format(analysis))
                else:
                    return["Analysis returned None", True]
            except RuntimeError as e:
                return["Analysis Failed {}".format(str(e)), True]
            if not str(selected_model) == "None":
                logger.info("Analysis with model id:{} {}".format(hackmodel, selected_model))
                analysis_simplified = str(analysis_simplified) + " With Model: " + selected_model
            return[analysis_simplified, True]
        else:
            # Pop Alert dialog
            logger.info("Nothing selected")
            return["Please Select Jobs", True]
    return["", False]

# Callback for reference model table updating
# Input:
#   create new model button click
#   delete model button click
# State:
#   recent jobs table selected and data
# Output:
#   text area on recent jobs screen
#   reference model table
#
# Output:
@app.callback(
    [
        dash.dependencies.Output('recent-job-model-status', 'children'),
        dash.dependencies.Output('table-ref-models', 'data'),
        dash.dependencies.Output('edit-model-div', 'style'),
        dash.dependencies.Output('edit-model-jobs-drdn', 'options'),
        dash.dependencies.Output('edit-model-jobs-drdn', 'value')
        # dash.dependencies.Output('table-multicol-sorting', 'selected_rows')
    ],
    [
        dash.dependencies.Input('save-newModel-btn', 'n_clicks_timestamp'),
        dash.dependencies.Input('delete-Model-btn', 'n_clicks_timestamp'),
        dash.dependencies.Input('toggle-Model-btn', 'n_clicks_timestamp'),
        dash.dependencies.Input('edit-Model-btn', 'n_clicks_timestamp'),
        dash.dependencies.Input('edit-Model-close-btn', 'n_clicks_timestamp'),
        # dash.dependencies.Input('edit-Model-save-btn', 'n_clicks_timestamp')
    ],
    [
        dash.dependencies.State('table-multicol-sorting', 'selected_rows'),
        dash.dependencies.State('table-multicol-sorting', 'data'),
        dash.dependencies.State('table-ref-models', 'selected_rows'),
        dash.dependencies.State('table-ref-models', 'data'),
        dash.dependencies.State('model-name-input', 'value'),
    ])
def update_output(save_model_btn, delete_model_btn, toggle_model_btn, edit_model_btn, edit_model_close_btn, sel_jobs, job_data, sel_refs, ref_data, model_name_input):
    selected_rows = []
    # Default Return Values
    edit_div_display_none = {'display': 'none'}
    jobs_drpdn_options = [{'label': 'No Jobs', 'value': 'No'}]
    jobs_drpdn_value = 'No'

    ref_df = refs.ref_df
    from .components import recent_button
    recentbtn = recent_button(
        {'save_model': save_model_btn,
         'delete_model': delete_model_btn,
         'toggle_model': toggle_model_btn,
         'edit_model': edit_model_btn,
         'close_edit': edit_model_close_btn,
         })
    logger.debug("--------------------------------------------------------")
    
# Create model
    if recentbtn is 'save_model':
        if sel_jobs:
            logger.debug("Model Name:{}".format(model_name_input))
            selected_rows = [(str(job_data[i]['job id']),job_data[i]['exp_name'],job_data[i]['exp_component']) for i in sel_jobs]
            # Verify jobs match, notify and return if not
            j,n,c = selected_rows[0]
            for j in selected_rows:
                if not (str(j[1]) == str(n) and str(j[2]) == str(c)):
                    logger.info(
                        "Bad job set, Name Comparison{} Component Comparison{}".format(str(j[1]) == str(n), str(j[2]) == str(c)))
                    return ["Jobs are incompatible", ref_df.to_dict('records'),
                            edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
            logger.info("Selected jobs {}".format(selected_rows))
            # Generate new refs for each of selected jobs
            from json import dumps
            # Make_refs returns a list of
            from .refs import make_refs
            refa = make_refs(name=model_name_input, jobs=[str(a) for a,b,c in selected_rows], tags={"exp_name":n,"exp_component":c})
            if refa is None:
                return ["Failed creating Reference Model", ref_df.to_dict('records'),
                            edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
            refa = pd.DataFrame(
                refa, columns=['id', 'name', 'date created', 'tags', 'jobs', 'features', 'active'])
            refa['jobs'] = refa['jobs'].apply(dumps)
            refa['tags'] = refa['tags'].apply(dumps)
            refa['features'] = refa['features'].apply(dumps)
            logger.info("Creating new model with \n{}".format(refa))
            refs.ref_df = pd.concat(
                [ref_df, refa], ignore_index=True, sort=False)
            # Sort by date to push new model to top
            refs.ref_df = refs.ref_df.sort_values(
                "date created",  # Column to sort on
                ascending = False,  # Boolean eval.
                inplace=False
            )
            return [model_name_input + " model created", refs.ref_df.to_dict('records'), edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
        return ["", ref_df.to_dict('records'),
                edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]

# Delete Model
    if recentbtn is 'delete_model':
        if sel_refs and len(sel_refs) > 0:
            selected_refs = [(ref_data[i]['id'],ref_data[i]['name']) for i in sel_refs]
            logger.info("Delete Model {}".format(selected_refs))
            for n in selected_refs:
                refs.ref_df = ref_df[ref_df.name != n[1]]
                from epmt_query import delete_refmodels
                delete_refmodels(n[0])
        return [selected_rows, ref_df.to_dict('records'),
                edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
# Toggle Active Status
    if recentbtn is 'toggle_model':
        if sel_refs and len(sel_refs) > 0:
            selected_refs = ref_data[sel_refs[0]]['name']
            logger.info("Toggle model name {} pre-invert active {}".format(
                selected_refs, ref_df[ref_df.name == selected_refs].active))
            # Where the 'name' is selected set 'active' as the np.invert of what it was
            refs.ref_df.loc[(ref_df.name == selected_refs),
                            'active'] = ~ref_df[ref_df.name == selected_refs].active
            logger.info(
                "post-invert active {}".format(refs.ref_df[ref_df.name == selected_refs].active))
        return [selected_rows, ref_df.to_dict('records'),
                edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
# Edit Model
    if recentbtn is 'edit_model':
        if sel_refs and len(sel_refs) > 0:
            selected_refs = ref_data[sel_refs[0]]
            # Hack for selected jobs
            from ast import literal_eval
            # These ref_jobs_li are the selected jobs in the selected model.jobs
            ref_jobs_li = literal_eval(ref_data[sel_refs[0]]['jobs'])
            logger.debug("evaled jobs are {}".format(ref_jobs_li))
            # Possible Jobs
            from .jobs import job_gen
            job_df = job_gen().df
            # Get Comparable jobs with tags 
            #from jobs import comparable_job_partitions
            from epmt_query import comparable_job_partitions
            logger.info("Seeking comparable jobs for {}".format(ref_jobs_li))
            # Pass in all jobs for now then filter out what we need
            comparable_jobs = comparable_job_partitions(job_df['job id'].tolist())
            logger.debug("Comparable jobs returns {}".format(comparable_jobs))
            # grab tag and find other jobs
            logger.debug("Tags are: {}".format(ref_data[sel_refs[0]]['tags']))
            from ast import literal_eval
            ast_tags = literal_eval(ref_data[sel_refs[0]]['tags'])
            tag_tup = (ast_tags['exp_name'],ast_tags['exp_component'])
            pos_ref_jobs_li = []
            for n in comparable_jobs:
                if n[0] == tag_tup:
                    # Possible Reference jobs list
                    pos_ref_jobs_li = n[1]
            logger.debug("Possible reference jobs {}".format(pos_ref_jobs_li))
            logger.debug("Model:{} \nJobs:{}".format(
                selected_refs['name'], ref_jobs_li))
            jobs_drpdn_options = [{'label': i, 'value': i} for i in pos_ref_jobs_li]
            return [selected_rows, refs.ref_df.to_dict('records'), {'display': 'contents'},
                    jobs_drpdn_options, [i for i in ref_jobs_li]]
# Close edit model
    if recentbtn is 'close_edit':
        return [selected_rows, refs.ref_df.to_dict('records'),
                edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]
    ref_df = ref_df.sort_values(
                "date created",  # Column to sort on
                ascending = False,  # Boolean eval.
                inplace=False
            )
    return [selected_rows, ref_df.to_dict('records'),
            edit_div_display_none, jobs_drpdn_options, jobs_drpdn_value]


######################## Select rows Callbacks ########################
@app.callback(
    [Output('model-selector-dropdown', 'options'),
    Output('model-selector-dropdown', 'value')],
    [
        Input('table-multicol-sorting', 'data'),
        Input('table-multicol-sorting', 'selected_rows'),
        # Input('table-multicol-sorting', '')
    ])
def f(job_data, sel_jobs):
    logger.debug("Testing selected jobs {} job data len {}".format(sel_jobs,len(job_data)))
    # Disregard selections that are stale
    if sel_jobs and all([k <= len(job_data) for k in sel_jobs]):
        try:
            selected_rows = [(str(job_data[i]['job id']),job_data[i]['exp_name'],job_data[i]['exp_component']) for i in sel_jobs]
            logger.info(
                "Find reference models for each job\nJobs:{}".format([j[0] for j in selected_rows]))
            # Check for matching models
            model_tags = {'exp_component':selected_rows[0][2], 'exp_name':selected_rows[0][1]}
            from json import dumps
            # model_tags = dumps(model_tags)
            from .refs import ref_gen
            ref_df = ref_gen().df
            drdn_options = [{'label': "Run Without Model",
                            'value': "None"}]
            for model in ref_df.to_dict('records'):
                logger.debug("{} vs {}".format(model['tags'],dumps(model_tags)))
                if model['tags'] == model_tags:
                # if dumps(model['tags']) == model_tags:
                    logger.debug("Found a matching model {}".format(model))
                    drdn_options.append({'label': model['name'] + " Tags:" + dumps(model['tags']) + " Created on:" + str(model['date created']),
                                    'value': model['name']})
                    drdn_value = model['name']
            if len(drdn_options) > 1:
                return (drdn_options, drdn_value)
        except KeyError:
            logger.warn("Threw Key error stale data likely")
    else:
        return [[{'label': "No Jobs Selected",
             'value': "None"}], "None"]
        # or
        # selected_rows=pd.DataFrame(rows).iloc[i]
    return [[{'label': "No Models Available",
             'value': "None"}], "None"]

# Custom Select all
# This callback
# https://community.plot.ly/t/data-table-select-all-rows/16619/2
# Input:
#       n_clicks is used to trigger this callback
# State:
#       The data is used to count the rows
#       The selected rows is used to determine if all or none should be
#            selected
# Output:
#       The datatable selected_rows will be updated


@app.callback(
    Output('table-multicol-sorting', "selected_rows"),
    [Input('index-select-all', 'n_clicks'), ],
    [State('table-multicol-sorting', "data"),
     State('table-multicol-sorting', "selected_rows")]
)
def select_all(n_clicks, data, selected_count):
    if selected_count:
        # If All rows selected
        if len(data) == len(selected_count):
            # Deselect all
            return []
    return [i for i in range(len(data))]


def format_bytes(size, roundn=2):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return (str(round(size, roundn)) + power_labels[n] + 'B')


def strfdelta(tdelta, fmt="{hours}:{minutes}:{seconds}"):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)

# Recent jobs data table callback
# inputs:
#   raw-switch - the toggle for converting datatypes (abbreviated)
#   new-data-button - a button for resetting the random jobs
#   searchdf - a text area that actively is run on keypress
#   row-count-dropdown - Requested number of rows per page

# outputs:
#   table, data - This is the data in the main jobs table
#   table, columns - The table column names can be changed
@app.callback(
    [Output('table-multicol-sorting', 'data'),
     Output('table-multicol-sorting', 'columns'),
     Output('table-multicol-sorting', "page_size"),
     Output('table-multicol-sorting', "page_count"),
     Output('table-multicol-sorting', "style_data_conditional")],
    [Input('raw-switch', 'value'),
     Input(component_id='searchdf', component_property='value'),
     Input(component_id='jobs-date-picker', component_property='end_date'),
     Input(component_id='row-count-dropdown',
           component_property='value'),  # Requested row limiter
     Input('table-multicol-sorting', "page_current"),  # Page Number - 1
     # Input('table-multicol-sorting', "page_size"),  # How many rows the table wants to have per page
     Input('table-multicol-sorting', "sort_by")  # What is requested to sort on
     ],
    [State(component_id='jobs-date-picker', component_property='start_date')])
def update_output(raw_toggle, search_value, end, rows_per_page, page_current, sort_by, start):
    logger.info("\nUpdate_output started")
    ctx = dash.callback_context
    # Debug Context due to this callback being huge
    logger.debug("Callback Context info:\nTriggered:\n{}\nInputs:\n{}\nStates:\n{}".format(
        ctx.triggered, ctx.inputs, ctx.states))
    from .jobs import job_gen
    logger.debug("Rows requested per page:{}".format(rows_per_page))
    offset = 0
    # Grab df
    job_df = job_gen().df
    import ui.refs as refs
    orig = job_df
    alt = orig.copy()
    # Limit by time
    if end:
        from datetime import datetime, timedelta
        logger.debug("Comparing df start days ({},...) with job-date-picker {}".format(
            job_df['start'][0].date(), datetime.strptime(start, "%Y-%m-%d").date()))
        time_mask = (job_df['start'].map(lambda x: x.date()) > datetime.strptime(start, "%Y-%m-%d").date() - timedelta(
            days=1)) & (job_df['start'].map(lambda x: x.date()) <= datetime.strptime(end, "%Y-%m-%d").date())
        logger.debug("Query: (Start:{} End:{})".format(start, end))
        alt = job_df.loc[time_mask]


    ctx = dash.callback_context
    # logger.info(value)

    # If Raw toggle is switched
    # Convert usertime to percentage
    # Return alt df of abbreviated data
    from json import dumps
    if raw_toggle:
        # Data for raw is not modified except for tags to text
        alt['tags'] = alt['tags'].apply(dumps)
    else:
        # Data for abbreviated is changed
        alt['usertime'] = alt['usertime'] / orig['cpu_time']
        alt['usertime'] = pd.Series(
            [float("{0:.2f}".format(val * 100)) for val in alt['usertime']], index=alt.index)
        alt['systemtime'] = alt['systemtime'] / orig['cpu_time']
        alt['systemtime'] = pd.Series(
            [float("{0:.2f}".format(val * 100)) for val in alt['systemtime']], index=alt.index)
        alt.rename(columns={
            'systemtime': 'systemtime (%cpu_time)',
            'usertime': 'usertime (%cpu_time)',
        }, inplace=True)

    # Convert Bytes
        in_units = alt['bytes_in'].tolist()
        in_units = get_unit(in_units)
        out_units = alt['bytes_out'].tolist()
        out_units = get_unit(out_units)
        logger.info("Input units {}b Output Units {}b".format(
            in_units, out_units))
        alt['bytes_in'] = alt['bytes_in'].apply(
            convtounit, reqUnit=in_units).round(2)  # .map('{:.2f}'.format)
        alt['bytes_out'] = alt['bytes_out'].apply(
            convtounit, reqUnit=out_units).round(2)  # .map('{:.2f}'.format)
        alt.rename(columns={
            'bytes_in': 'bytes_in ({}b)'.format(in_units),
            'bytes_out': 'bytes_out ({}b)'.format(out_units),
        }, inplace=True)

    # Convert durations
        alt['duration'] = pd.to_timedelta(alt['duration'], unit='us').apply(
            lambda x: x*10000).apply(strfdelta)
        alt['duration'] = pd.to_datetime(
            alt['duration'], format="%H:%M:%S").dt.time
        alt['cpu_time'] = pd.to_timedelta(alt['cpu_time'], unit='us').apply(
            lambda x: x * 10000).apply(strfdelta)
        alt['cpu_time'] = pd.to_datetime(
            alt['cpu_time'], format="%H:%M:%S").dt.time
        alt.rename(columns={'cpu_time': 'cpu_time (HH:MM:SS)',
                            'duration': 'duration (HH:MM:SS)'}, inplace=True)
        # Parse out wanted tag columns
        new = alt[['job id', 'tags']]
        b =  new.tags.apply(pd.Series)
        # Only Display Specific tags from dash_config
        from .dash_config import tags_to_display
        #tags_df = c[tags_to_display]
        # Merge those changes into the end of the alt.df
        alt = pd.merge(alt, b, left_index=True, right_index=True)
        # Convert tags into a string that can be searched
        alt['tags'] = alt['tags'].apply(dumps)
    # #################################################################
    # Run the search
    try:
        if raw_toggle:
            # Raw search on job id only
            results = alt[(alt['job id'].str.contains(search_value))
                | (alt['tags'].str.contains(search_value))]
        else:
            # Search on abbreviated data and tags as columns
            results = alt[(alt['exp_name'].str.contains(search_value))
                        | (alt['job id'].str.contains(search_value))
                        | (alt['exp_component'].str.contains(search_value))
                        | (alt['tags'].str.contains(search_value))]
        logger.info("Found {} search results on \"{}\"".format(int(results.shape[0]),search_value))
        alt = results
    except Exception as e:
        logger.error(
            "Threw exception on query\nexception: ({})".format(e))
    
    # Recalculate number of rows after search complete
    from math import ceil
    len_jobs = int(alt.shape[0])
    num_pages = ceil(len_jobs / int(rows_per_page))
    logger.debug("Pages = ceil({} / {}) = {}".format(len_jobs,
                                                     int(rows_per_page), num_pages))
    
    # #################################################################
    # Sort
    if len(sort_by):
        # Need to check if sorting on a existing column
        if sort_by[0]['column_id'] in alt.columns.tolist():
            alt = alt.sort_values(
                sort_by[0]['column_id'],  # Column to sort on
                ascending=sort_by[0]['direction'] == 'asc',  # Boolean eval.
                inplace=False
            )

    # #################################################################
    # Calculate Comparable jobs and generate custom highlighting
    # Only attempt if there are jobs to run on
    custom_highlights = []
    if len_jobs>0:
        #from jobs import comparable_job_partitions
        from epmt_query import comparable_job_partitions
        comparable_jobs = comparable_job_partitions(alt['job id'].tolist())
        # Generate contrasting colors from length of comparable sets
        from .components import list_of_contrast
        cont_colors = list_of_contrast(len(comparable_jobs), start = (200, 200, 120))
        for color, n in enumerate(comparable_jobs, start=0):
            # Only generate a rule if more than one job in rule
            if len(n[1]) > 1:
                custom_highlights.append({'if': {'filter_query': '{exp_component} = "' + n[0][1] + '" && {exp_name} = "' + n[0][0] + '"'},
                                          'backgroundColor': cont_colors[color]})
            else:
                #logger.debug("Not generating a highlight rule for {} not enough matching jobs".format(n))
                pass
    else:
        logger.debug("Not enough jobs to do highlighting Len Jobs = {}".format(len_jobs))
    #logger.debug("Custom Highlights: \n{}".format(custom_highlights))

    # #################################################################
    # Last reduce df down to 1 page view based on requested page and rows per page
    alt = alt.iloc[page_current *
                         int(rows_per_page):(page_current + 1) * int(rows_per_page)]
    logger.info("Update_output complete")
    # #################################################################
    # #################################################################
    # #################################################################
    return [
        alt.to_dict('records'),  # Return the table records
        [{"name": i, "id": i} for i in alt.columns] if raw_toggle else [
            {"name": i, "id": i} for i in alt.columns ],# if i is not 'tags'],  # hide tags if raw_toggle false
        int(rows_per_page),  # Custom page size
        num_pages,  # Custom Page count
        [] if raw_toggle else custom_highlights   # Custom Highlighting on matching job tags
    ]

######################## /Index Callbacks ########################

######################## Create Ref Callback ########################


######################## /Create Ref Callbacks ########################
