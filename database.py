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
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    photos = relationship('Photos', backref='vk_user_id')


class Photos(Base):
    """Таблица для хранения фото пользователей"""

    __tablename__ = 'photos'
    vk_id = sq.Column(sq.Integer, sq.ForeignKey('user.vk_id'))
    url = sq.Column(sq.String, primary_key=True)


def create_tables():
    """Создание таблиц, если они отсутствуют."""
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(e)


def add_user(id, first_name, last_name, photos=None):
    """Добавление пользователя или партнера в базу данных.
    """

    if get_user(id):
        return 'Эта запись уже существует'

    if photos is None:
        photos = []
    user = User(vk_id=id,
                first_name=first_name,
                last_name=last_name
                )

    for photo in photos:
        user.photos.append(Photos(vk_id=id, url=photo))
    session.add(user)

    session.commit()
    return 'Пользователь добавлен'


def get_user(id):
    return session.query(User).get(id)
