import os, re
from django.core.exceptions import ImproperlyConfigured
from pathlib import Path  # python3 only

def dotenv_values(dotenv_path):
    lines = []
    with open(dotenv_path) as fp:
        lines = fp.read().splitlines()

    # get tuples of values,property splitting each line of the file
    lines = map(lambda l: tuple(re.split(r'\s*=\s*', l, 1)), filter(None, lines))
    lines = list(lines);
    print(f"dotenv_values: found {len(lines)} valid lines")
    if not lines:
        return dict()
    return dict(lines)

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


# e.g. set ENV=production to get .production.env file
dotenv_filename = '.{0}.env'.format(os.environ.get('ENV', '')) if 'ENV' in os.environ else '.env'
dotenv_path = str(Path('.') / dotenv_filename)
dotenv_dict = dotenv_values(dotenv_path=dotenv_path)

print('loading env file: {0}'.format(dotenv_filename))
