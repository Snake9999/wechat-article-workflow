from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pathlib import Path

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)

    title = Column(String(500), nullable=False)
    source_name = Column(String(255), default="")
    source_url = Column(String(1000), unique=True, index=True, nullable=False)
    publish_time = Column(String(100), default="")
    cover_image = Column(String(1000), default="")

    raw_html_path = Column(String(1000), default="")
    cleaned_md_path = Column(String(1000), default="")
    dan_koe_md_path = Column(String(1000), default="")
    humanized_md_path = Column(String(1000), default="")
    draft_result_path = Column(String(1000), default="")

    status = Column(String(100), default="created")
    error_message = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def 初始化数据库(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
