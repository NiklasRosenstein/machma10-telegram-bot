
import contextlib
import functools
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import nr.proxy
from deprecated import deprecated
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import func as F

from .utils.sqlalchemy.guc import GucHelper

LOGGER = logging.getLogger(__name__)
Base = declarative_base()
Session = sessionmaker()
session = nr.proxy.threadlocal(
    name=__name__ + '.session',
    error_message=
        '({name}) No SqlAlchemy session is available. Ensure that you are using the '
        'make_session() context manager before accessing the global session proxy.',
)

__all__ = [
    'Base',
    'Session',
    'session',
    'initialize_db',
    'Exercise',
    'ExerciseAlias',
    'User',
    'UserReps',
    'F',
]


def initialize_db(*args, create_tables: bool = False, **kwargs):
    """
    Creates an SqlAlchemy engine and configures the #Session class. The arguments are
    forwarded to the #create_engine() function (see [1]).

    [1]: https://docs.sqlalchemy.org/en/13/core/engines.html#sqlalchemy.create_engine
    """

    LOGGER.info('Initializing SqlAlchemy Session')
    engine = create_engine(*args, **kwargs)
    Session.configure(bind=engine)

    if create_tables:
        Base.metadata.create_all(engine)


@contextlib.contextmanager
def make_session() -> None:
    """
    A context manager that creates a new #Session object and makes it available in the global
    #session proxy object.
    """

    nr.proxy.push(session, Session())
    try:
        yield
    except:
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        nr.proxy.pop(session)


def async_session(func):
    """
    Decorator for an async function that wraps it in a #make_session() call to ensure
    that a session is available.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with make_session():
            return await func(*args, **kwargs)

    return wrapper


def get(entity, **pks) -> GucHelper:
    return GucHelper(session, entity, **pks)


class Exercise(Base):
    __tablename__ = 'exercises'

    exercise_name = Column(String, primary_key=True)
    exercise_link = Column(String, nullable=True)
    aliases = relationship('ExerciseAlias', back_populates='exercise', cascade='all, delete-orphan')
    reps = relationship('UserReps', back_populates='exercise', cascade='all, delete-orphan', lazy='subquery')


class ExerciseAlias(Base):
    __tablename__ = 'exercise_aliases'

    exercise_alias = Column(String, primary_key=True)
    exercise_name = Column(String, ForeignKey('exercises.exercise_name'))
    exercise = relationship('Exercise', back_populates='aliases')


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    reps = relationship('UserReps', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')


class UserReps(Base):
    __tablename__ = 'user_reps'

    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    exercise_name = Column(String, ForeignKey('exercises.exercise_name'), primary_key=True)
    reps = Column(Integer, nullable=False)

    user = relationship('User', back_populates='reps')
    exercise = relationship('Exercise', back_populates='reps')
