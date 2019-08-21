# general.py
from sqlalchemy import *
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
#import settings
#engine = engine_from_config(settings.db_params, prefix='')

