import settings


if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *

# API
# commented functions are implemented in ORM-specific files.
# We provide them here for completeness:

# get_(model, pk=None, **kwargs)
# Query a model to get a single instance or None (if no match)
#
# get_(User, 25)
# get_(Job, '6355501')
# or use keywords as below,
# get_(User, name='John.Doe')
#
#
# Below are API calls that have the same implementation on all ORMs
#
def get_or_create_(model, **kwargs):
    return (get_(model, **kwargs) or create_(model, **kwargs))
