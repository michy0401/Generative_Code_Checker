"""Verifica si quien hace un request tiene derecho a operar sobre una revision existente
(regenerarla, ver su historial, etc.).

Regla (ver Parte B de la tarea de regeneracion):
- Si la revision tiene `student_id` (fue creada por un usuario autenticado), el requester
  debe estar autenticado y su `student_id` (del JWT) debe coincidir exactamente.
- Si la revision es anonima (`student_id` es None), el requester debe mandar el `session_id`
  exacto de esa revision. El student_id de un JWT, si vino, no aplica en este caso.
"""


def is_owner(review, student_id=None, session_id=None):
    """True si el requester es dueno de `review` (dict con al menos student_id/session_id)."""
    owner_student_id = review.get("student_id")
    if owner_student_id is not None:
        return student_id is not None and student_id == owner_student_id

    return session_id is not None and session_id == review.get("session_id")
