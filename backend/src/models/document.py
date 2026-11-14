from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Text,ForeignKey,UniqueConstraint
from src.config.database import Base
class TokenDocument(Base):
 __tablename__='token_documents'
 __table_args__=(UniqueConstraint('version_id','reference',name='uq_version_reference'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 corpus_id:Mapped[int]=mapped_column(ForeignKey('corpora.id'))
 version_id:Mapped[int|None]=mapped_column(ForeignKey('corpus_versions.id'),nullable=True)
 reference:Mapped[str]=mapped_column(String(80))
 title:Mapped[str]=mapped_column(String(120))
 tokens_text:Mapped[str]=mapped_column(Text)
