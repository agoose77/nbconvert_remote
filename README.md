# nbconvert_remote (`nbconvert_http`)
HTTP frontend to `nbconvert`. Only exposes configuration support (via nested dictionaries) for the REST API.
Exposes both web and REST-JSON frontends (on `/` and `/api/convert` respectively)

Install with pip: `pip install git+https://github.com/agoose77/nbconvert_remote.git#egg=nbconvert_http`

# Usage
## Web
* Launch from shell `nbconvert-http`. 
* Navigate to `/` on the appropriate address (host, port), default "0.0.0.0"(localhost), 8000.
## REST
* Send JSON object with the format `{'notebook': ..., 'exporter': ...}`. Optionally pass `'config'` key to set configuration data (see [nbconvert](https://nbconvert.readthedocs.io/en/latest/config_options.html)).
* Parse JSON response with the format `{'body': ..., 'resources': ..., 'mime-type': ...}` where `'body'` will be a Base-64 encoded string if the result of nbconvert was bytes. 
