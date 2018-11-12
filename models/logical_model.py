# 
# Logical Model
#

from pony.orm import *
import time, datetime
from .general import db

# User running experiment or frepp
class User(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	username = Required(str,unique=True)
	exps = Set('Experiment')
	pps = Set('PostProcessRun')

# Build/version/etc
class Platform(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	platform_name = Required(str)
	exps = Set('Experiment')
	pps = Set('PostProcessRun')

# Frerun - run of a model.
# Creates an experiment
class Experiment(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	pps = Set('PostProcessRun')
	user = Required(User)
	platform = Required(Platform)

# Frepp - run of a post processing pipeline against data from a model run. 
# Appends to or replaces data in an experiment.
class PostProcessRun(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	experiment = Required(Experiment)
	jobs = Set('Job')
	user = Required(User)
	platform = Required(Platform)
# TODO: Store all the below in a dict(), it's metadata
	command = Required(str)
	input_filename = Required(str)
	input_file_contents = Required(str)
	indir = Required(str)
	outdir = Required(str)
