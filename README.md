# nbconvert_remote (`nbconvert_http`)
HTTP frontend to `nbconvert`. Only exposes configuration support (via nested dictionaries) for the REST API.
Exposes both web and REST-JSON frontends (on `/` and `/api/convert` respectively)

Install with pip: `pip install git+https://github.com/agoose77/nbconvert_remote.git#egg=nbconvert_http`

# Usage
## Web
* Launch from shell `nbconvert-http`. 
* Navigate to `/` on the appropriate address (host, port), default `("0.0.0.0", 8000)`.
Note, the web interface uses a custom LaTeX template for LaTeX derived exporters, in order to support citations. Defining a cell with the tag `bibliography` will cause the cell to be hidden, and its contents passed to LaTeX as a bib file.
![Web usage screen recording](https://i.imgur.com/lna8jK5.gif)
## REST
* Send JSON object to `/api/convert` with the format `{'notebook': ..., 'exporter': ...}`. Optionally pass `'config'` key to set configuration data (see [nbconvert](https://nbconvert.readthedocs.io/en/latest/config_options.html)).
* Parse JSON response with the format `{'body': ..., 'resources': ..., 'mime-type': ...}` where `body` will be a Base-64 encoded string if the result of nbconvert was bytes. 
