
import contextlib
import datetime

from sqlalchemy import create_engine

from sqlalchemy import Column
from sqlalchemy import BigInteger
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy import UniqueConstraint
from sqlalchemy.types import Enum

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.exc

import settings


Base = declarative_base()

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

Session = scoped_session(sessionmaker())
Session.configure(bind=engine)

dlstate_enum   = Enum('new', 'fetching', 'complete', 'error', name='dlstate_enum')


@contextlib.contextmanager
def session_context():
	session = Session()
	try:
		yield session
	finally:
		Session.remove()

class WebPages(Base):

	__tablename__ = 'web_pages'
	name = 'web_pages'

	id                = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key = True)
	state             = Column(dlstate_enum, default='new', index=True, nullable=False)
	errno             = Column(Integer, default='0')
	url               = Column(Text, nullable = False, index = True, unique = True)

	mimetype          = Column(Text)
	is_text           = Column(Boolean, default=False)

	content           = Column(Text)

	fetchtime         = Column(DateTime, default=datetime.datetime.min, index=True)
	addtime           = Column(DateTime, default=datetime.datetime.utcnow)



class NuReleaseItem(Base):
	__tablename__ = 'nu_release_item'
	id               = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)

	actual_target    = Column(Text)
	page_title       = Column(Text)

	fetch_tries      = Column(Integer, default='0')

	seriesname       = Column(Text, nullable=False, index=True)
	releaseinfo      = Column(Text)
	groupinfo        = Column(Text, nullable=False, index=True)
	referrer         = Column(Text, nullable=False)
	outbound_wrapper = Column(Text, nullable=False, unique=True)

	release_date     = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
	first_seen       = Column(DateTime, nullable=False, default=datetime.datetime.min)

	__table_args__ = (
		UniqueConstraint('seriesname', 'releaseinfo', 'groupinfo', 'outbound_wrapper'),
		)
