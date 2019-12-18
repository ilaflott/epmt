from datetime import datetime as dt
from datetime import date, timedelta
from datetime import datetime
import plotly.graph_objs as go
from plotly import tools
import numpy as np
import pandas as pd

from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name
pd.options.mode.chained_assignment = None


# Return dictionary query results
def parseurl(i):
    logger.info("Given URL {}".format(i))
    # convert url into dictionary
    from urllib.parse import parse_qs, urlparse
    res_dict = parse_qs(urlparse(i).query)
    logger.info("URL2Dict {}".format(res_dict))
    return res_dict

# Takes dictionary button:timestamp
# Returns most recent
def recent_button(btn_dict):
    if sum(btn_dict.values()) > 0:
        recent = max(btn_dict, key=lambda key: btn_dict[key])
        logger.debug("Button click {}".format(recent))
        return recent
    return None


# Check if string time has 1 or 2 colons and convert grabbing just time
def conv_str_time(st):
    logger.info("Convert to time")
    import datetime
    if st.count(':') == 1:
        return datetime.datetime.strptime(st[1][1],"%H:%M").time()
    # limit functionality for now
    #if st.count(':') == 2:
    #    return datetime.datetime.strptime(st[1][1],"%H:%M:%S").time()
    else:
        return None

# Get greatest unit from df
power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T', 5: 'P'}
def get_unit(alist):
    if len(alist) > 0:
        hi = max(alist)
    else:
        hi = 1
    from math import log
    #print(alist)
    return power_labels[int(log(hi,1024))]


# Convert df value used with get_unit
def convtounit(val,reqUnit):
    # Letter to Unit reverse search
    unitp = list(power_labels.keys())[list(power_labels.values()).index(reqUnit)]
    return val/1000**unitp

import colorsys
def contrasting_color(color):
    if not color:
        return self.first_track_color;

    # How much to jump in hue:
    jump = .16
    (r,g,b) = colorsys.hsv_to_rgb(color[0] + jump,
                                  color[1],
                                  color[2])
    hexout = '#%02x%02x%02x' % (int(r),int(g),int(b))
    return ((r,g,b),hexout)
((r,g,b), hex)= contrasting_color(colorsys.rgb_to_hsv(50, 100, 200))


def list_of_contrast(length, start=(0,0,0)):
    l = []
    for n in range(length):
        ((r,g,b),hex) = contrasting_color(colorsys.rgb_to_hsv(start[0],start[1],start[2]))
        l.append(hex)
        start = (r, g, b)
    return l
