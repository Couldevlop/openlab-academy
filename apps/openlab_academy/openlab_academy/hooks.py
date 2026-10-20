app_name = "openlab_academy"
app_title = "OpenLab Academy"
app_publisher = "Openlab Consulting"
app_description = "Personnalisation OpenLab Academy pour Frappe LMS"
app_email = "contact@openlabconsulting.com"
app_license = "agpl-3.0"
required_apps = ["lms"]

after_install = "openlab_academy.entrypoints.install.after_install"
after_migrate = ["openlab_academy.entrypoints.install.after_migrate"]
after_request = ["openlab_academy.entrypoints.http.after_request"]
app_include_css = ["/assets/openlab_academy/css/openlab.css"]
web_include_css = ["/assets/openlab_academy/css/openlab.css"]

override_whitelisted_methods = {"lms.lms.utils.get_lesson": "openlab_academy.entrypoints.lms.get_lesson"}
doc_events = {
    "LMS Quiz Submission": {"before_insert": "openlab_academy.entrypoints.lms.avant_soumission_quiz"},
    "LMS Assignment Submission": {
        "before_insert": "openlab_academy.entrypoints.lms.avant_soumission_devoir",
        "after_insert": "openlab_academy.entrypoints.evaluation.rendu",
        "on_update": "openlab_academy.entrypoints.evaluation.rendu",
    },
}
