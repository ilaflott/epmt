#!/usr/bin/env python
import settings
from models import db, db_session, User, Platform, Experiment, PostProcessRun
from logging import getLogger, basicConfig, DEBUG
logger = getLogger(__name__)  # you can use other name

# An XML file has multiple experiments
# each experiment has a user, platform, metadata, inputdir, outputdir
# 
@db_session
def lookup_or_create_User(username):
	mn = User.get(username=username)
	if mn is None:
		logger.debug("Creating User %s",username)
		mn = User(username=username)
        else:
		logger.debug("Found %s",mn)
	return mn

@db_session
def lookup_or_create_Platform(platform_name):
	mn = Platform.get(platform_name=platform_name)
	if mn is None:
		logger.debug("Creating Platform %s",platform_name)
		mn = Platform(platform_name=platform_name)
        else:
		logger.debug("Found %s",mn)
	return mn

@db_session
def lookup_or_create_Experiment(experiment_name, username, platform_name, metadata={}):
    p = lookup_or_create_Platform(platform_name)
    u = lookup_or_create_User(username)
    e = Experiment.get(experiment_name=experiment_name,user=u,platform=p)
    if e is None:
        logger.debug("Creating Experiment %s, %s, %s, %s",experiment_name,username,platform_name,metadata)
        e = Experiment(experiment_name=experiment_name, user=u, platform=p, info_dict=metadata)
        # Add experiment to reverse relations
        p.exps.add(e)
        u.exps.add(e)
    else:
        logger.debug("Found %s %s, %s, %s",e,experiment_name,username,platform_name)
    return e

# For our purposes this is a FREPP run at the moment
@db_session
def lookup_or_create_PostProcessRun(experiment_name, username, platform_name, metadata={}):
	e = lookup_or_create_Experiment(experiment_name, username, platform_name, metadata)
        ppr = PostProcessRun.get(user=e.user, platform=e.platform, experiment=e)
        if ppr is None:
            logger.debug("Creating PostProcessRun %s, %s, %s, %s",experiment_name,username,platform_name,metadata)
            ppr = PostProcessRun(user=e.user, platform=e.platform, experiment=e, info_dict=metadata)
            e.pprs.add(ppr)
        else:
            logger.debug("Found %s %s, %s, %s",ppr,experiment_name,username,platform_name)
        return e, ppr

basicConfig(level=DEBUG)
db.bind(**settings.db_params)
#if __name__ == '__main__':
db.generate_mapping(create_tables=True)
db.drop_all_tables(with_all_data=True)
db.create_tables()
metadata = { "metadata1": "value1", "metadata2": "value2" }
e, ppr = lookup_or_create_PostProcessRun("exp_name","exp_user","exp_platform", metadata)    
logger.debug("%s %s",e,ppr)
e, ppr = lookup_or_create_PostProcessRun("exp_name","exp_user2","exp_platform2", metadata)
logger.debug("%s %s",e,ppr)
e, ppr = lookup_or_create_PostProcessRun("exp_name2","exp_user2","exp_platform", metadata)
logger.debug("%s %s",e,ppr)
e, ppr = lookup_or_create_PostProcessRun("exp_name2","exp_user","exp_platform2", metadata)
logger.debug("%s %s",e,ppr)
# This updates existing
e, ppr = lookup_or_create_PostProcessRun("exp_name2","exp_user","exp_platform2", metadata)
logger.debug("%s %s",e,ppr)
#else
#    db.generate_mapping(create_tables=False)

