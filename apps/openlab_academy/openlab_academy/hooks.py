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
# fiche d'un parcours : bouton « Inscrits et gratuités » (offrir le parcours à un apprenant, ou le rendre payant)
doctype_js = {"LMS Course": "public/js/gratuites_parcours.js"}
web_include_css = ["/assets/openlab_academy/css/openlab.css",
                   # site public (accueil, catalogue, fiche) ; chargé après la charte, qu'il réutilise
                   "/assets/openlab_academy/css/site.css"]

# l'accueil du site est la façade publique de l'académie, et non la page du LMS : c'est elle qu'on trouve
# avant de savoir ce qu'on cherche. Les apprenants connectés gardent /lms.
home_page = "accueil"

# écrans d'évaluation (relecture, correcteur, retour) : une page, routée côté navigateur
website_route_rules = [{"from_route": "/espace/<path:app_path>", "to_route": "espace"},
                       # fiche publique d'un parcours : un seul segment, le nom ne sort pas du préfixe
                       {"from_route": "/parcours/<parcours>", "to_route": "parcours-public"},
                       # parcours fermé : destination d'un refus de la fenêtre d'accès (page publique)
                       {"from_route": "/parcours-ferme/<cours>", "to_route": "parcours-ferme"}]

# parcours en retard de paiement : présentation, leçons, quiz et réponses refusés par l'API (ParcoursBloque), documents
# et listes retirés par les permissions, progression et certificat refusés. Nos hooks has_permission ne font que
# refuser (None sinon) : Frappe retient le premier avis non nul, un True court-circuiterait les refus du LMS.
override_whitelisted_methods = {
    "lms.lms.api.get_translations": "openlab_academy.entrypoints.langue.get_translations",
    "lms.lms.utils.get_lesson": "openlab_academy.entrypoints.lms.get_lesson",
    "lms.lms.utils.get_course_details": "openlab_academy.entrypoints.lms.get_course_details",
    # catalogue, accueil, recherche et cohortes limités aux parcours visibles (agents jamais filtrés)
    "lms.lms.utils.get_courses": "openlab_academy.entrypoints.catalogue.get_courses",
    "lms.lms.utils.get_course_count": "openlab_academy.entrypoints.catalogue.get_course_count",
    "lms.lms.api.get_my_courses": "openlab_academy.entrypoints.catalogue.get_my_courses",
    "lms.lms.utils.get_related_courses": "openlab_academy.entrypoints.catalogue.get_related_courses",
    "lms.lms.utils.get_batches": "openlab_academy.entrypoints.catalogue.get_batches",
    "lms.lms.api.get_my_batches": "openlab_academy.entrypoints.catalogue.get_my_batches",
    "lms.lms.utils.get_batch_details": "openlab_academy.entrypoints.catalogue.get_batch_details",
    "lms.command_palette.search_sqlite": "openlab_academy.entrypoints.catalogue.search_sqlite",
    "lms.lms.utils.get_batch_courses": "openlab_academy.entrypoints.catalogue.get_batch_courses",
    "lms.lms.utils.get_batch_count": "openlab_academy.entrypoints.catalogue.get_batch_count",
    "lms.lms.utils.get_course_categories": "openlab_academy.entrypoints.catalogue.get_course_categories",
    "lms.lms.api.get_chart_details": "openlab_academy.entrypoints.catalogue.get_chart_details",
    "lms.lms.utils.get_reviews": "openlab_academy.entrypoints.catalogue.get_reviews",
    "lms.lms.utils.get_program_details": "openlab_academy.entrypoints.catalogue.get_program_details",
    "lms.lms.utils.get_order_summary": "openlab_academy.entrypoints.catalogue.get_order_summary",
    "lms.lms.utils.get_course_outline": "openlab_academy.entrypoints.lms.get_course_outline",
    "lms.lms.utils.get_quiz_with_questions": "openlab_academy.entrypoints.lms.get_quiz_with_questions",
    "lms.lms.doctype.lms_quiz.lms_quiz.check_answer": "openlab_academy.entrypoints.lms.check_answer",
    "lms.lms.api.mark_lesson_progress": "openlab_academy.entrypoints.lms.mark_lesson_progress",
    "lms.lms.doctype.course_lesson.course_lesson.save_progress": "openlab_academy.entrypoints.lms.save_progress",
    # médias privés des leçons (allow_guest) : suivent le refus de leur parcours
    "lms.lms.doctype.course_lesson.course_lesson.serve_resource": "openlab_academy.entrypoints.lms.serve_resource",
    "lms.lms.doctype.lms_certificate.lms_certificate.create_certificate":
        "openlab_academy.entrypoints.lms.create_certificate",
}
has_permission = {d: "openlab_academy.entrypoints.lms.lecture_permise"
                  for d in ("Course Lesson", "Course Chapter", "LMS Quiz", "LMS Assignment", "LMS Programming Exercise")}
permission_query_conditions = {
    "Course Lesson": "openlab_academy.entrypoints.lms.conditions_lecons",
    "Course Chapter": "openlab_academy.entrypoints.lms.conditions_chapitres",
    "LMS Quiz": "openlab_academy.entrypoints.lms.conditions_quiz",
    "LMS Assignment": "openlab_academy.entrypoints.lms.conditions_devoirs",
    "LMS Programming Exercise": "openlab_academy.entrypoints.lms.conditions_exercices",
}
doc_events = {
    "User": {"after_insert": "openlab_academy.entrypoints.langue.initialiser_langue"},
    "LMS Course": {"on_update": ["openlab_academy.entrypoints.paiement.parcours_enregistre",
                                 "openlab_academy.infrastructure.retouches_frappe.retouche"]},
    # inscription directe à un parcours payant refusée hors cohorte (le dossier naît de l'inscription à la cohorte)
    # puis rattachée à la cohorte-fenêtre d'un parcours limité à ses dates
    "LMS Enrollment": {
        "before_insert": "openlab_academy.entrypoints.paiement.avant_inscription_parcours",
        "after_insert": ["openlab_academy.entrypoints.lancement.rejoindre_cohorte",
                         # parcours offert : le dossier naît quand même, puis se dispense
                         "openlab_academy.entrypoints.paiement.apres_inscription_parcours"],
    },
    "LMS Batch Enrollment": {
        "before_insert": "openlab_academy.entrypoints.paiement.avant_inscription",
        "after_insert": "openlab_academy.entrypoints.paiement.apres_inscription",
    },
    # une pièce retouchée dans l'application n'est plus réécrite par le fichier de parcours
    "Course Lesson": {"on_update": "openlab_academy.infrastructure.retouches_frappe.retouche",
                      "on_trash": "openlab_academy.infrastructure.parties_frappe.oublier"},
    "LMS Assignment": {"on_update": "openlab_academy.infrastructure.retouches_frappe.retouche"},
    "LMS Question": {"on_update": "openlab_academy.infrastructure.retouches_frappe.retouche"},
    # une partie de séance enregistrée met la leçon à jour, sans toucher aux autres parties
    "Partie Lecon OpenLab": {"on_update": "openlab_academy.infrastructure.parties_frappe.marquer"},
    "LMS Quiz Submission": {"before_insert": "openlab_academy.entrypoints.lms.avant_soumission_quiz"},
    "LMS Certificate": {"before_insert": "openlab_academy.entrypoints.lms.avant_certificat"},
    "LMS Assignment Submission": {
        "before_insert": "openlab_academy.entrypoints.lms.avant_soumission_devoir",
        "after_insert": "openlab_academy.entrypoints.evaluation.rendu",
        "on_update": "openlab_academy.entrypoints.evaluation.rendu",
    },
}

# échéances de la chaîne de correction : rien ne bloque une copie ; instantanés des dépôts rendus à la minute ;
# rappels de paiement chaque jour à 08:00 et retrait du catalogue des parcours dont la fenêtre est close à 00:05
# (Abidjan = UTC)
scheduler_events = {
    "hourly": ["openlab_academy.entrypoints.evaluation.traiter_echeances"],
    "cron": {
        "* * * * *": ["openlab_academy.entrypoints.evaluation.instantaner_rendus"],
        "0 8 * * *": ["openlab_academy.entrypoints.paiement.envoyer_rappels"],
        "5 0 * * *": ["openlab_academy.entrypoints.lancement.retirer_parcours_echus"],
    },
}
