"""База данных для хранения пользователей vk, всех найденных потенциальных партнеров, избранных партнеров и
позиции пользователя в его треде.
"""

import sqlalchemy as sq
from config import username, password, database
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

Base = declarative_base()
engine = sq.create_engine(f'postgresql://{username}:{password}@localhost:5432/{database}')
Session = sessionmaker(bind=engine)
session = Session()


class User(Base):
    """Таблица для хранения информации о пользователе: идентификатор строки в базе данных, идентификатор vk, фамилия,
    имя, возраст, пол и город.
       """

    __tablename__ = 'user'
    vk_id = sq.Column(sq.Integer, primary_key=True)
    # first_name = sq.Column(sq.String)
    # last_name = sq.Column(sq.String)
    # photos = relationship('Photos', backref='vk_user_id')


class Searcher(Base):
    """Таблица для хранения данных искателя"""

    __tablename__ = 'searchers'
    # first_name = sq.Column(sq.String)
    # last_name = sq.Column(sq.String)
    bdate = sq.Column(sq.Integer)
    sex = sq.Column(sq.Integer)
    city = sq.Column(sq.Integer)
    vk_id = sq.Column(sq.Integer, primary_key=True)
    offset = sq.Column(sq.Integer)
    step = sq.Column(sq.Integer)  # 0 - bdate, 1 - sex, 2 - city


def create_tables():
    """Создание таблиц, если они отсутствуют."""
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(e)


def add_user(id):
    """Добавление пользователя или партнера в базу данных.
    """

    if get_user(id):
        return 'Эта запись уже существует'

    user = User(vk_id=id)

    session.add(user)

    session.commit()
    return 'Пользователь добавлен'


def get_user(id):
    return session.query(User).get(id)


def pop_user():
    user = session.query(User).first()
    if user:
        session.delete(user)
        session.commit()
        return user
    else:
        return None


def fill_searcher(id, bdate, sex, city):
    searcher = session.query(Searcher).get(id)

    if searcher:
        return
    searcher = Searcher(vk_id=id, bdate=bdate, sex=sex, city=city, offset=0)
    session.add(searcher)
    session.commit()
