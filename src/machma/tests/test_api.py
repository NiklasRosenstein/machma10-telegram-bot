
import functools
import os
import pytest

import nr.proxy

from machma import api, db
from .dummy_data import create_dummy_data


def with_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        do_echo = os.getenv('SQL_DEBUG', '').strip().lower() in ('1', 'true', 'yes')
        db.initialize_db('sqlite:///:memory:', create_tables=True, echo=do_echo)
        nr.proxy.push(db.session, db.Session())
        create_dummy_data()
        try:
            return func(*args, **kwargs)
        finally:
            nr.proxy.pop(db.session)
    return wrapper


@with_db
def test_get_user():
    assert api.get_user(1)['first_name'] == 'Eve'
    assert api.get_user(2)['first_name'] == 'John'
    assert api.get_user(3) is None


@with_db
def test_has_user():
    assert api.has_user(1)
    assert api.has_user(2)
    assert not api.has_user(3)


@with_db
def test_get_max_reps():
    assert api.get_max_reps() == {'Dips': 30, 'Crunches': 80, 'Situps': 20}


@with_db
def test_get_max_reps_for_exercise():
    assert api.get_max_reps_for_exercise('Dips') == 30
    assert api.get_max_reps_for_exercise('Crunches') == 80
    assert api.get_max_reps_for_exercise('Situps') == 20


@with_db
def test_get_user_reps():
    assert api.get_user_reps(1) == {'Dips': 30, 'Crunches': 50, 'Situps': 20}
    assert api.get_user_reps(2) == {'Dips': 10, 'Crunches': 80, 'Situps': 0}

    with pytest.raises(api.UserDoesNotExistError):
        api.get_user_reps(3)

    api.add_user(3, None, 'Test', None)
    assert api.get_user_reps(3) == {'Dips': 0, 'Crunches': 0, 'Situps': 0}


@with_db
def test_get_user_reps_for_exercise():
    assert api.get_user_reps_for_exercise(1, 'Dips') == 30
    assert api.get_user_reps_for_exercise(1, 'Crunches') == 50
    assert api.get_user_reps_for_exercise(1, 'Situps') == 20

    assert api.get_user_reps_for_exercise(2, 'Dips') == 10
    assert api.get_user_reps_for_exercise(2, 'Crunches') == 80
    assert api.get_user_reps_for_exercise(2, 'Situps') == 0

    with pytest.raises(api.UserDoesNotExistError):
        api.get_user_reps_for_exercise(3, 'Situps')
    with pytest.raises(api.ExerciseDoesNotExistError):
        api.get_user_reps_for_exercise(2, 'Badoof')


@with_db
def test_get_user_todo_reps():
    assert api.get_user_todo_reps(1) == {'Dips': 0, 'Crunches': 30, 'Situps': 0}
    assert api.get_user_todo_reps(2) == {'Dips': 20, 'Crunches': 0, 'Situps': 20}

    with pytest.raises(api.UserDoesNotExistError):
        api.get_user_todo_reps(3)

    api.add_user(3, None, 'Test', None)
    assert api.get_user_todo_reps(3) == {'Dips': 30, 'Crunches': 80, 'Situps': 20}


@with_db
def test_get_user_todo_reps_for_exercise():
    assert api.get_user_todo_reps_for_exercise(1, 'Dips') == 0
    assert api.get_user_todo_reps_for_exercise(1, 'Crunches') == 30
    assert api.get_user_todo_reps_for_exercise(1, 'Situps') == 0

    assert api.get_user_todo_reps_for_exercise(2, 'Dips') == 20
    assert api.get_user_todo_reps_for_exercise(2, 'Crunches') == 0
    assert api.get_user_todo_reps_for_exercise(2, 'Situps') == 20

    with pytest.raises(api.UserDoesNotExistError):
        api.get_user_todo_reps_for_exercise(3, 'Situps')
    with pytest.raises(api.ExerciseDoesNotExistError):
        api.get_user_todo_reps_for_exercise(2, 'Badoof')


@with_db
def test_add_to_user_reps__update_existing():
    # Update existing user reps.
    assert api.get_user_reps_for_exercise(1, 'Dips') == 30
    api.add_to_user_reps(1, 'Dips', 10)
    assert api.get_user_reps_for_exercise(1, 'Dips') == 40


@with_db
def test_add_to_user_reps__create_new():
    # Create new user reps. First assert that the reps row doesn't exist yet.
    assert db.get_or_none(db.UserReps, on=dict(user_id=2, exercise_name='Situps')) is None
    assert api.get_user_reps_for_exercise(2, 'Situps') == 0
    assert api.get_user_reps(2)['Situps'] == 0
    assert api.get_user_todo_reps_for_exercise(2, 'Situps') == 20

    api.add_to_user_reps(2, 'Situps', 555)
    assert api.get_user_reps_for_exercise(2, 'Situps') == 555
    assert api.get_user_reps(2)['Situps'] == 555
    assert api.get_user_todo_reps_for_exercise(2, 'Situps') == 0

    # Now assert that the reps row exists.
    assert db.get(db.UserReps, on=dict(user_id=2, exercise_name='Situps')) is not None


@with_db
def test_get_exercise_by_alias():
    assert api.get_exercise_by_alias('Triceps') == 'Dips'
    assert api.get_exercise_by_alias('Whales') is None


@with_db
def test_add_alias():
    assert not api.has_alias('Foobar')
    api.add_alias('Foobar', 'Crunches')
    assert api.has_alias('Foobar')


@with_db
def test_has_alias():
    assert api.has_alias('Triceps')
    assert not api.has_alias('Whales')


@with_db
def test_has_exercise():
    assert api.has_exercise('Dips')
    assert not api.has_exercise('Foobar')


@with_db
def test_add_exercise():
    assert not api.has_exercise('Jumps')
    assert not api.has_alias('Jumps')
    api.add_exercise('Jumps', 'https://lmgtfy.com/?q=jumps')
    assert api.has_exercise('Jumps')
    assert api.has_alias('Jumps')


@with_db
def test_get_exercises():
    assert api.get_exercises() == {
        'Dips': {'link': 'https://www.stack.com/a/dips'},
        'Crunches': {'link': None},
        'Situps': {'link': None},
    }


@with_db
def test_set_exercise_link():
    assert api.get_exercises()['Crunches']['link'] is None
    api.set_exercise_link('Crunches', 'https://goo.gl/Crunches')
    assert api.get_exercises()['Crunches']['link'] == 'https://goo.gl/Crunches'


@with_db
def test_add_user():
    with pytest.raises(api.UserDoesNotExistError):
        api.get_user_reps(3)
    api.add_user(3, None, 'Third', None)
    assert api.get_user_reps(3) == {'Dips': 0, 'Crunches': 0, 'Situps': 0}


@with_db
def test_e2e_scenario1():
    """
    This test scenario replicates what the interactions with the database when a user
    adds reps for an exercise for the first time. Among other things, it ensures that
    the API uses outer joins when determining the max and user reps.
    """

    assert api.has_user(2)
    assert not api.has_exercise('Foo')
    assert not api.has_alias('Foo')

    api.add_exercise('Foo', 'https://foo.sport')
    assert api.has_exercise('Foo')
    assert api.has_alias('Foo')

    assert api.get_user_reps_for_exercise(2, 'Situps') == 0
    assert api.get_user_reps_for_exercise(2, 'Foo') == 0
    assert api.get_user_todo_reps_for_exercise(2, 'Situps') == 20
    assert api.get_user_todo_reps_for_exercise(2, 'Foo') == 0

    api.add_to_user_reps(2, 'Situps', 20)
    api.add_to_user_reps(2, 'Foo', 30)

    assert api.get_user_reps_for_exercise(2, 'Situps') == 20
    assert api.get_user_reps_for_exercise(2, 'Foo') == 30
    assert api.get_user_todo_reps_for_exercise(2, 'Situps') == 0
    assert api.get_user_todo_reps_for_exercise(2, 'Foo') == 0
