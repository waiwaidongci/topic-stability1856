from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Integer,ForeignKey,UniqueConstraint,DateTime
from datetime import datetime,timezone
from src.config.database import Base
class CorpusVersion(Base):
 __tablename__='corpus_versions'
 __table_args__=(UniqueConstraint('corpus_id','version_no',name='uq_corpus_version_no'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 corpus_id:Mapped[int]=mapped_column(ForeignKey('corpora.id'))
 version_no:Mapped[int]=mapped_column(Integer)
 shard_total:Mapped[int]=mapped_column(Integer)
 status:Mapped[str]=mapped_column(String(20),default='receiving')
 created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class CorpusShard(Base):
 __tablename__='corpus_shards'
 __table_args__=(UniqueConstraint('version_id','shard_index',name='uq_version_shard_index'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 version_id:Mapped[int]=mapped_column(ForeignKey('corpus_versions.id'))
 shard_index:Mapped[int]=mapped_column(Integer)
 content_hash:Mapped[str]=mapped_column(String(64))
 document_count:Mapped[int]=mapped_column(Integer)
 created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
