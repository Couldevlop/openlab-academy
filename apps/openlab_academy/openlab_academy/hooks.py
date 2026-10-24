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
# parcours en retard de paiement : pages redirigées vers le paiement (chargement complet d'une page)
before_request = ["openlab_academy.entrypoints.http.before_request"]
app_include_css = ["/assets/openlab_academy/css/openlab.css"]
app_include_js = ["/assets/openlab_academy/js/simulateur_impact.js"]
web_include_css = ["/assets/openlab_academy/css/openlab.css"]

# écrans d'évaluation (relecture, correcteur, retour) : une page, routée côté navigateur
website_route_rules = [{"from_route": "/espace/<path:app_path>", "to_route": "espace"}]

# parcours en retard de paiement : présentation, leçons, quiz et réponses refusés par l'API (ParcoursBloque), documents
# et listes retirés par les permissions, progression et certificat refusés. Nos hooks has_permission ne font que
# refuser (None sinon) : Frappe retient le premier avis non nul, un True court-circuiterait les refus du LMS.
override_whitelisted_methods = {
    "lms.lms.utils.get_lesson": "openlab_academy.entrypoints.lms.get_lesson",
    "lms.lms.utils.get_course_details": "openlab_academy.entrypoints.lms.get_course_details",
    "lms.lms.utils.get_quiz_with_questions": "openlab_academy.entrypoints.lms.get_quiz_with_questions",
    "lms.lms.doctype.lms_quiz.lms_quiz.check_answer": "openlab_academy.entrypoints.lms.check_answer",
    "lms.lms.api.mark_lesson_progress": "openlab_academy.entrypoints.lms.mark_lesson_progress",
    "lms.lms.doctype.course_lesson.course_lesson.save_progress": "openlab_academy.entrypoints.lms.save_progress",
    "lms.lms.doctype.lms_certificate.lms_certificate.create_certificate":
        "openlab_academy.entrypoints.lms.create_certificate",
}
has_permission = {d: "openlab_academy.entrypoints.lms.lecture_permise"
                  for d in ("Course Lesson", "Course Chapter", "LMS Quiz", "LMS Assignment", "LMS Programming Exercise")}
permission_query_conditions = {
    "Course Lesson": "openlab_academy.entrypoints.lms.conditions_lecons",
    "LMS Quiz": "openlab_academy.entrypoints.lms.conditions_quiz",
    "LMS Assignment": "openlab_academy.entrypoints.lms.conditions_devoirs",
    "LMS Programming Exercise": "openlab_academy.entrypoints.lms.conditions_exercices",
}
doc_events = {
    "LMS Course": {"on_update": "openlab_academy.entrypoints.paiement.parcours_enregistre"},
    # inscription directe à un parcours payant refusée hors cohorte (le dossier naît de l'inscription à la cohorte)
    "LMS Enrollment": {"before_insert": "openlab_academy.entrypoints.paiement.avant_inscription_parcours"},
    "LMS Batch Enrollment": {
        "before_insert": "openlab_academy.entrypoints.paiement.avant_inscription",
        "after_insert": "openlab_academy.entrypoints.paiement.apres_inscription",
    },
    "LMS Quiz Submission": {"before_insert": "openlab_academy.entrypoints.lms.avant_soumission_quiz"},
    "LMS Certificate": {"before_insert": "openlab_academy.entrypoints.lms.avant_certificat"},
    "LMS Assignment Submission": {
        "before_insert": "openlab_academy.entrypoints.lms.avant_soumission_devoir",
        "after_insert": "openlab_academy.entrypoints.evaluation.rendu",
        "on_update": "openlab_academy.entrypoints.evaluation.rendu",
    },
}

# échéances de la chaîne de correction : rien ne bloque une copie ; instantanés des dépôts rendus à la minute ;
# rappels de paiement chaque jour à 08:00 (Abidjan = UTC)
scheduler_events = {
    "hourly": ["openlab_academy.entrypoints.evaluation.traiter_echeances"],
    "cron": {
        "* * * * *": ["openlab_academy.entrypoints.evaluation.instantaner_rendus"],
        "0 8 * * *": ["openlab_academy.entrypoints.paiement.envoyer_rappels"],
    },
}
