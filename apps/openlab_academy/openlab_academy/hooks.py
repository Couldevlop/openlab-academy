app_name = "openlab_academy"
app_title = "OpenLab Academy"
app_publisher = "Openlab Consulting"
app_description = "Personnalisation OpenLab Academy pour Frappe LMS"
app_email = "contact@openlabconsulting.com"
app_license = "agpl-3.0"
required_apps = ["lms"]

after_install = "openlab_academy.entrypoints.install.after_install"
after_request = ["openlab_academy.entrypoints.http.after_request"]
app_include_css = ["/assets/openlab_academy/css/openlab.css"]
web_include_css = ["/assets/openlab_academy/css/openlab.css"]
