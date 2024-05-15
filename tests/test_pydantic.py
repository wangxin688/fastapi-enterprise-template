from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from src.core.models.base import Base


class TestModel(Base):
    __tablename__ = "test"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str | None] = mapped_column(unique=True)
    t_id: Mapped[int] = mapped_column(ForeignKey("test1.id", ondelete="CASCADE"))
    test1: Mapped["Test1Model"] = relationship(back_populates="test")


class Test1Model(Base):
    __tablename__ = "test1"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    test: Mapped[list[TestModel]] = relationship(back_populates="test1")


engine = create_engine("sqlite://", echo=True)

Base.metadata.create_all(engine)

with Session(engine) as session:
    t = TestModel(name="test", email="test", t_id=1)
    session.add(TestModel(name="test", email="test", t_id=1))
    session.commit()
    print(t.__dict__)
    print(t.test1)
