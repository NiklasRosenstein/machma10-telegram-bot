
import contextlib
import functools
import logging
from typing import Any, Dict, Optional, Type, TypeVar

import nr.proxy
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_
from sqlalchemy import func as F

LOGGER = logging.getLogger(__name__)
Base = declarative_base()
Session = sessionmaker()
session = nr.proxy.threadlocal[Session](
    name=__name__ + '.session',
    error_message=
        '({name}) No SqlAlchemy session is available. Ensure that you are using the '
        'make_session() context manager before accessing the global session proxy.',
)

T_Base = TypeVar('T_Base', bound=Base)


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


def get(
    entity: Type[T_Base],
    on: Dict[str, Any],
    then_update: Optional[Dict[str, Any]] = None,
    or_create: Optional[Dict[str, Any]] = None,
) -> T_Base:
    """
    Returns a row from the specified *entity* that matches the columns specified in *on*.
    Depending on the arguments, the instance will then be updated with the values from
    *then_update*, or a new row will be created from the merged values of *on* and *or_create*.
    """

    filters = and_(*(getattr(entity, k) == v for k, v in on.items()))
    query = session.query(entity).filter(filters)

    try:
        instance = query.one()
    except NoResultFound:
        if or_create is not None:
            instance = entity(**on, **or_create)
            session.add(instance)
        else:
            raise
    else:
        if then_update is not None:
            for key, value in then_update.items():
                setattr(instance, key, value)
            session.add(instance)

    return instance


def get_or_none(
    entity: Type[T_Base],
    on: Dict[str, Any],
    then_update: Optional[Dict[str, Any]] = None,
) -> Optional[T_Base]:
    try:
        return get(entity, on=on, then_update=then_update)
    except NoResultFound:
        return None


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
