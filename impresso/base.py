import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values
from pathlib import Path  # python3 only

# e.g. set ENV=production to get .production.env file
dotenv_filename = '.{0}.env'.format(os.environ.get('ENV', '')) if 'ENV' in os.environ else '.env'
dotenv_path = Path('.') / dotenv_filename
dotenv_dict = dotenv_values(dotenv_path=dotenv_path, verbose=True)

# print('loading env file: {0}'.format(dotenv_filename))

def get_env_variable(var_name, default=None):
    if var_name in dotenv_dict:
        return dotenv_dict[var_name]
    try:
        return os.environ[var_name]
    except KeyError:
        if default:
            return default
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)
