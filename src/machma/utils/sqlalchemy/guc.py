
"""
Provides a helper class to perform a Get and Update or Create operation.

Example:

```py
>>> GucHelper(session, User, id=user_id)\
...     .then_update(name='Name: ' + User.name)\
...     .or_create(name='Name: John')\
...     .done()
<User object>
```

If #GucHelper.then_update() is used, it will raise a #NoResultFound exception when no
row matching the specified primary keys exists unless #GucHelper.or_create() or
#GucHelper.or_none() is used.
"""

from typing import Any, Dict, Optional, Type

from sqlalchemy.sql import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session

Base = Any  #: SqlAlchemy declrative base


class GucHelper:

    def __init__(self, _session: Session, _entity: Type[Base], **pks: Dict[str, Any]):
        self._session = _session
        self._entity = _entity
        self._pks = pks
        self._update = None
        self._create = None
        self._or_none = False

    def then_update(self, **cols: Dict[str, Any]) -> 'GucHelper':
        """
        Update the instance if it exists. If this is used, but the instance does not exist
        and #or_create() is not used, a #NoResultFound will be raised.
        """

        assert self._update is None, "then_update() already called"
        self._update = cols
        return self

    def or_create(self, **cols: Dict[str, Any]) -> 'GucHelper':
        """
        If the instance doesn't exist, create a new one with the primary keys specified
        in the #GucHelper constructor and the specified *cols*.
        """

        assert self._create is None, "or_create() already called"
        assert not self._or_none, "or_create() cannot be called if or_none() was already called"
        self._create = cols
        return self

    def or_none(self) -> 'GucHelper':
        """
        If the instance doesn't exist, skip the update and return #None from #done(). This
        can only be called after #then_update().
        """

        assert self._update is not None, "or_none() can only be called after then_update()"
        assert self._create is None, "or_none() cannot be called if or_create() was already called"
        self._or_none = True
        return self

    def done(self) -> Optional[Base]:
        """
        Apply the operations built with the #GucHelper methods. Returns the updated or
        created instance.
        """

        filters = and_(*(getattr(self._entity, k) == v for k, v in self._pks.items()))
        query = self._session.query(self._entity).filter(filters)
        try:
            instance = query.one()
        except NoResultFound:
            if self._create is not None:
                instance = self._entity(**self._pks, **self._create)
                self._session.add(instance)
            elif self._or_none or self._update is None:
                instance = None
            else:
                raise
        else:
            if self._update is not None:
                for key, value in self._update.items():
                    setattr(instance, key, value)
                self._session.add(instance)
        return instance
