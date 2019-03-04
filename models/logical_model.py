# 
# Logical Model
#

from pony.orm import *
from .general import db
import datetime

class PostProcessRun(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	# The following four are from the environment currently
	component = Required(str)
	name = Required(str)
	jobname = Required(str)
	oname = Required(str)
	# End
	user = Required('User')
	job = Required('Job')
	detectors = Set('Detector')
	# 
	# component = Optional('Component')
	# platform = Optional('Platform')
	# experiment = Optional('Experiment')

class Detector(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	name = PrimaryKey(str)
	description = Optional(str)
	pandas_json = Optional(Json)
 	pprs = Set('PostProcessRun')

# 
# Unused for now
#

#class Experiment(db.Entity):
# 	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
# 	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
# 	info_dict = Optional(Json)
# 	# end template
# 	experiment_name = Required(str)
# 	component = Required(str)
# 	user = Required('User')
# 	platform = Required('Platform')
# #	PrimaryKey(experiment_name, user.username, platform)
# 	pprs = Set('PostProcessRun')

# # 
# # Unused for now
# #
# class Platform(db.Entity):
# 	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
# 	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
# 	info_dict = Optional(Json)
# 	# end template
# 	platform_name = PrimaryKey(str)
# 	exps = Set('Experiment')
# 	pprs = Set('PostProcessRun')

# #	composite_index(experiment, user, platform)
	
# # TODO: Store all the below in a dict(), it's metadata
# #	command = Required(str)
# #	input_filename = Required(str)
# #	input_file_contents = Required(str)
# #	indir = Required(str)
# #	outdir = Required(str)
