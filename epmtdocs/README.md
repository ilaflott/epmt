Static Site generator
----
This directory is where the static documentation site is generated using mkdocs.
----
The nature of mkdocs requires documentation to be within the mkdocs subdirectories.  To navigate this issue I've linked the needed markdown files in the epmtdocs/docs/ directory. Those markdown files are then referenced in the configuration stored in mkdocs.yml.  This yml configures everything from pages, themes, plugins to colors used.

A specific configuration worthy of note is:

`use_directory_urls: false`

This ensures hyperlinks generated lead to direct html files, not directories containing index.html files.

The root url redirection is defined in the static web server serve_static.py.  Currently visiting localhost:8000/ in mkdocs serve leads to page not found and a menu bar of other available pages.  

Visiting the root url with the server from epmt gui: localhost:8080/ will direct to readme_ui.html appropriately.

----
----
----
First install mkdocs:

`pip install mkdocs`

To serve a live updating server for a temporary view of the site:

```
epmt/epmtdocs $ mkdocs serve
INFO    -  Building documentation... 
INFO    -  Cleaning site directory 
[I 200424 08:55:54 server:296] Serving on http://127.0.0.1:8000
```

Visiting the provided url will result in page not found.  This is due to there being no index.html in the site root directory.  The root case is handled by the static server.

Once happy with the live view, build the static site:
(This will generate html in the site directory)

`epmt/epmtdocs $ mkdocs build`

You now have the most current HTML site matching the markdown documentation linked.