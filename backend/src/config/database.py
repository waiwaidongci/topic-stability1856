from sqlalchemy import create_engine,inspect,text
from sqlalchemy.orm import DeclarativeBase,sessionmaker
from .settings import DATABASE_URL
class Base(DeclarativeBase): pass
_kwargs={'pool_pre_ping':True}
if DATABASE_URL.startswith('mysql'):_kwargs['isolation_level']='READ COMMITTED'
engine=create_engine(DATABASE_URL,**_kwargs)
SessionLocal=sessionmaker(engine,expire_on_commit=False)
def get_db():
 with SessionLocal() as db: yield db
def ensure_schema():
 if 'corpus_versions' not in inspect(engine).get_table_names():return
 with engine.begin() as conn:
  if 'version_id' not in {c['name'] for c in inspect(engine).get_columns('token_documents')}:
   conn.execute(text('ALTER TABLE token_documents ADD COLUMN version_id INT NULL'))
   conn.execute(text('ALTER TABLE token_documents ADD CONSTRAINT fk_tokdoc_version FOREIGN KEY (version_id) REFERENCES corpus_versions(id)'))
  uniques={tuple(u['column_names']):u['name'] for u in inspect(engine).get_unique_constraints('token_documents')}
  if ('corpus_id','reference') in uniques:
   if 'idx_tokdoc_corpus' not in {i['name'] for i in inspect(engine).get_indexes('token_documents')}:conn.execute(text('ALTER TABLE token_documents ADD INDEX idx_tokdoc_corpus (corpus_id)'))
   conn.execute(text(f"ALTER TABLE token_documents DROP INDEX `{uniques[('corpus_id','reference')]}`"))
  if ('version_id','reference') not in uniques:conn.execute(text('ALTER TABLE token_documents ADD CONSTRAINT uq_version_reference UNIQUE (version_id,reference)'))
  if 'corpus_version_id' not in {c['name'] for c in inspect(engine).get_columns('topic_runs')}:
   conn.execute(text('ALTER TABLE topic_runs ADD COLUMN corpus_version_id INT NULL'))
   conn.execute(text('ALTER TABLE topic_runs ADD CONSTRAINT fk_run_version FOREIGN KEY (corpus_version_id) REFERENCES corpus_versions(id)'))
