"""Tests unitarios del ownership check (services.review_ownership.is_owner).

Sin red, sin servidor, sin Supabase real: is_owner() opera sobre dicts en memoria.
"""

import services.review_ownership as review_ownership


def test_authenticated_review_same_student_id_is_owner():
    review = {"student_id": "user-1", "session_id": None}
    assert review_ownership.is_owner(review, student_id="user-1") is True


def test_authenticated_review_different_student_id_is_not_owner():
    review = {"student_id": "user-1", "session_id": None}
    assert review_ownership.is_owner(review, student_id="user-2") is False


def test_authenticated_review_anonymous_requester_is_not_owner():
    # session_id no aplica cuando la revision tiene student_id: sin JWT (student_id=None)
    # no es el dueno, aunque mande cualquier session_id.
    review = {"student_id": "user-1", "session_id": None}
    assert review_ownership.is_owner(review, student_id=None, session_id="cualquiera") is False


def test_anonymous_review_matching_session_id_is_owner():
    review = {"student_id": None, "session_id": "sess-1"}
    assert review_ownership.is_owner(review, session_id="sess-1") is True


def test_anonymous_review_different_session_id_is_not_owner():
    review = {"student_id": None, "session_id": "sess-1"}
    assert review_ownership.is_owner(review, session_id="sess-2") is False


def test_anonymous_review_missing_session_id_is_not_owner():
    review = {"student_id": None, "session_id": "sess-1"}
    assert review_ownership.is_owner(review) is False


def test_anonymous_review_authenticated_requester_is_not_owner():
    # Un JWT valido no sirve para una revision anonima si no se manda tambien
    # el session_id exacto (el student_id del JWT se ignora en este branch).
    review = {"student_id": None, "session_id": "sess-1"}
    assert review_ownership.is_owner(review, student_id="user-1") is False
