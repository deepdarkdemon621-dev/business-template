from sqlalchemy.orm import DeclarativeBase

from app.core.database import Base


def test_base_is_declarative():
    assert issubclass(Base, DeclarativeBase)


def test_base_has_metadata():
    assert Base.metadata is not None
