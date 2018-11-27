# 
# Logical Model
#

from pony.orm import *
from .general import db
import datetime

# User running experiment or frepp
class User(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	username = PrimaryKey(str)
	exps = Set('Experiment')
	pprs = Set('PostProcessRun')

# Build/version/etc
class Platform(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	platform_name = PrimaryKey(str)
	exps = Set('Experiment')
	pprs = Set('PostProcessRun')

# Frerun - run of a model, creates an experiment
class Experiment(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	experiment_name = Required(str)
	user = Required(User)
	platform = Required(Platform)
#	PrimaryKey(experiment_name, user.username, platform)
	pprs = Set('PostProcessRun')

# Frepp - run of post processing on model data, appends or replaces data related to an experiment
class PostProcessRun(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	# Currently these are the same as in the experiment
	experiment = Required(Experiment)
	user = Required(User)
	platform = Required(Platform)
	jobs = Set('Job')
#	composite_index(experiment, user, platform)
	
# TODO: Store all the below in a dict(), it's metadata
#	command = Required(str)
#	input_filename = Required(str)
#	input_file_contents = Required(str)
#	indir = Required(str)
#	outdir = Required(str)
