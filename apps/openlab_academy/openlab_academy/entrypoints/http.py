"""Hook Frappe after_request : habille les pages HTML de l'interface /lms."""
from openlab_academy.infrastructure.habillage import injecter


def _est_page_lms(chemin: str) -> bool:
    return chemin == "/lms" or chemin.startswith("/lms/")


def after_request(response, request) -> None:
    if response.direct_passthrough or response.mimetype != "text/html" or not _est_page_lms(request.path):
        return
    response.set_data(injecter(response.get_data(as_text=True)))
