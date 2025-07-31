"""
EPMT settings module - loads default settings and user-specific overrides.
"""
# load defaults
from epmt.epmt_default_settings import (
    bulk_insert, db_params, env_blacklist, epmt_output_prefix, epmt_settings_kind, 
    error_dest, ingest_failed_dir, ingest_remove_on_success, input_pattern, install_prefix,
    job_tags_env, jobid_env_list, lazy_compute_process_tree, logfile, max_log_statement_length, 
    orm, outlier_features, outlier_features_blacklist, outlier_thresholds, papiex_options, 
    papiex_options_bycpu, papiex_options_byhost, per_process_fields, post_process_job_on_ingest, 
    profile, retire_jobs_ndays, retire_jobs_per_delete_max, retire_models_ndays, 
    skip_for_thread_sums, stage_command, stage_command_dest, univariate_classifiers, verbose
)

# from logging import getLogger, basicConfig, ERROR
# basicConfig(level=ERROR)
# logger = getLogger(__name__)

# import sys
# logger.debug("attempting import of user settings")
# logger.debug("sys.path entries are:")
# for path in sys.path:
#    logger.debug(f"path={path}")

# now load the user-specific settings.py so they override the defaults
try:
    import epmt.settings as user_settings
    # Import all public attributes from user settings to override defaults
    for attr_name in dir(user_settings):
        if not attr_name.startswith('_'):
            globals()[attr_name] = getattr(user_settings, attr_name)
except Exception as e:
    raise ModuleNotFoundError('alternate epmt.settings import approach did not' +
                              ' work and neither did the first attempt!') from e
# else:
#    logger.debug('epmt_settings imported successfully! yay!!!')


# epmt_settings_kind=''
# db_params = {'url': 'sqlite:///:memory:', 'echo': False}
