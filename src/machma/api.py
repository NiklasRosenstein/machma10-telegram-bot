
"""
Provides an API to interact with the database.
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm.exc import NoResultFound

from . import db
from .db import session, Exercise, ExerciseAlias, User, UserReps, F


class ApiError(Exception):

    def __init__(self, entity_id: Any, message: Optional[str] = None):
        self.entity_id = entity_id
        self.message = message

    def __str__(self):
        result = repr(self.entity_id)
        if self.message:
            result += ': ' + self.message
        return result


class UserError(ApiError):
    pass


class UserDoesNotExistError(UserError):
    pass


class ExerciseError(ApiError):
    pass


class ExerciseDoesNotExistError(ExerciseError):
    pass


def _get_max_reps():
    return (session
        .query(Exercise.exercise_name, F.max(F.coalesce(UserReps.reps, 0)).label('reps'))
        .group_by(Exercise.exercise_name)
        .outerjoin(UserReps)
    )


def _get_user_reps(user_id: int):
    # Ensure that the user actually exists.
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise UserDoesNotExistError(user_id)
    # Get a subquery for the reps of that user.
    user_reps = user.reps.subquery()
    # Left outer join the reps on th exercises.
    query = (session
        .query(Exercise.exercise_name, F.coalesce(user_reps.c.reps, 0).label('reps'))
        .select_from(Exercise)
        .outerjoin(user_reps)
    )
    return query


def _get_user_todo_reps(user_id: int):
    max_reps = _get_max_reps().subquery()
    user_reps = _get_user_reps(user_id).subquery()
    return (
        session
        .query(
            max_reps.c.exercise_name.label('exercise_name'),
            (max_reps.c.reps - user_reps.c.reps).label('reps'),
        )
        .select_from(
            max_reps.join(user_reps, max_reps.c.exercise_name == user_reps.c.exercise_name)
        )
    )


def _get_reps_for_exercise(query, exercise: str) -> int:
    # TODO(NiklasRosenstein): This doesn't seem quite like the right way to do this.
    #   Check https://stackoverflow.com/q/63728782/791713 for suggestions.
    query = query.subquery()
    query = session.query(*query.c).filter(query.c.exercise_name == exercise)
    try:
        return query.one()[1]
    except NoResultFound:
        raise ExerciseDoesNotExistError(exercise)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    user = session.query(User).filter(User.user_id == user_id).first()
    if user:
        return {
            'id': user.user_id,
            'user_name': user.user_name,
            'first_name': user.first_name,
            'last_name': user.last_name}
    return None


def has_user(user_id: int) -> bool:
    return session.query(User).filter(User.user_id == user_id).count() != 0


def get_max_reps() -> Dict[str, int]:
    return dict(_get_max_reps())


def get_max_reps_for_exercise(exercise: str) -> int:
    return _get_reps_for_exercise(_get_max_reps(), exercise)


def get_user_reps(user_id: int) -> Dict[str, int]:
    return dict(_get_user_reps(user_id))


def get_user_reps_for_exercise(user_id: int, exercise: str):
    return _get_reps_for_exercise(_get_user_reps(user_id), exercise)


def get_user_todo_reps(user_id: int) -> Dict[str, int]:
    return dict(_get_user_todo_reps(user_id))


def get_user_todo_reps_for_exercise(user_id: int, exercise: str) -> int:
    return _get_reps_for_exercise(_get_user_todo_reps(user_id), exercise)


def add_to_user_reps(user_id: int, exercise: str, reps: int) -> None:
    if not has_exercise(exercise):
        raise ExerciseDoesNotExistError(exercise)
    (db.get(UserReps, user_id=user_id, exercise_name=exercise)
        .then_update(reps=UserReps.reps + reps)
        .or_create(reps=reps)
        .done())


def get_exercise_by_alias(alias: str) -> Optional[str]:
    row = (session.query(ExerciseAlias.exercise_name)
        .filter(ExerciseAlias.exercise_alias == alias).first())
    if row:
        return row[0]
    return None


def add_alias(alias, exercise):
    session.add(ExerciseAlias(exercise_alias=alias, exercise_name=exercise))


def has_alias(alias: str) -> None:
    return (session.query(ExerciseAlias)
        .filter(ExerciseAlias.exercise_alias == alias).count()) > 0


def has_exercise(exercise: str) -> None:
    return (session.query(Exercise)
        .filter(Exercise.exercise_name == exercise).count()) > 0


def add_exercise(exercise: str, link: Optional[str] = None) -> None:
    session.add(Exercise(exercise_name=exercise, exercise_link=link))
    session.add(ExerciseAlias(exercise_alias=exercise, exercise_name=exercise))


def get_exercises() -> Dict[str, Dict[str, Any]]:
    rows = session.query(Exercise).all()
    return {r.exercise_name: {'link': r.exercise_link} for r in rows}


def set_exercise_link(exercise: str, link: Optional[str]) -> None:
    db.get(Exercise, exercise_name=exercise).then_update(exercise_link=link).done()


def add_user(
    user_id: int,
    user_name: Optional[str],
    first_name: str,
    last_name: Optional[str],
) -> None:
    session.add(User(user_id=user_id, user_name=user_name, first_name=first_name, last_name=last_name))
