
from machma.db import session, Exercise, ExerciseAlias, User, UserReps


def create_dummy_data():
    """
    Creates dummy entries in the database.
    """

    u1 = User(user_id=1, first_name='Eve')
    session.add(u1)

    u2 = User(user_id=2, first_name='John')
    session.add(u2)

    e1 = Exercise(exercise_name='Dips', exercise_link='https://www.stack.com/a/dips')
    session.add(e1)

    e2 = Exercise(exercise_name='Crunches')
    session.add(e2)

    e3 = Exercise(exercise_name='Situps')
    session.add(e3)

    session.add(UserReps(user_id=u1.user_id, exercise_name=e1.exercise_name, reps=30))
    session.add(UserReps(user_id=u2.user_id, exercise_name=e1.exercise_name, reps=10))
    session.add(UserReps(user_id=u1.user_id, exercise_name=e2.exercise_name, reps=50))
    session.add(UserReps(user_id=u2.user_id, exercise_name=e2.exercise_name, reps=80))
    session.add(UserReps(user_id=u1.user_id, exercise_name=e3.exercise_name, reps=20))

    session.add(ExerciseAlias(exercise_alias='Triceps', exercise_name=e1.exercise_name))
