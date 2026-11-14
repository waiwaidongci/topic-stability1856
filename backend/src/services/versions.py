import hashlib,json
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.models import Corpus,CorpusVersion,CorpusShard,TokenDocument,TopicRun
from src.constants.enums import VersionStatus
from src.utils.serialize import row
from .audit import record
MAX_VERSION_DOCUMENTS=1000
def shard_hash(documents):
 canonical=[{'reference':d.reference,'title':d.title,'tokens_text':d.tokens_text} for d in sorted(documents,key=lambda d:d.reference)]
 return hashlib.sha256(json.dumps(canonical,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def lock_corpus(db,corpus_id):
 corpus=db.scalar(select(Corpus).where(Corpus.id==corpus_id).with_for_update())
 if not corpus:raise HTTPException(404,'语料不存在')
 return corpus
def active_version(db,corpus_id):return db.scalar(select(CorpusVersion).where(CorpusVersion.corpus_id==corpus_id,CorpusVersion.status==VersionStatus.ACTIVE))
def version_state(db,version):
 shards=db.scalars(select(CorpusShard).where(CorpusShard.version_id==version.id).order_by(CorpusShard.shard_index)).all()
 received={s.shard_index for s in shards}
 return {**row(version),'received_shards':[{'shard_index':s.shard_index,'document_count':s.document_count,'content_hash':s.content_hash[:12]} for s in shards],'missing_shards':[i for i in range(version.shard_total) if i not in received],'document_count':sum(s.document_count for s in shards)}
def list_versions(db,corpus_id):
 if not db.get(Corpus,corpus_id):raise HTTPException(404,'语料不存在')
 return [version_state(db,v) for v in db.scalars(select(CorpusVersion).where(CorpusVersion.corpus_id==corpus_id).order_by(CorpusVersion.version_no))]
def create_version(db,corpus_id,data,user):
 lock_corpus(db,corpus_id)
 existing=db.scalar(select(CorpusVersion).where(CorpusVersion.corpus_id==corpus_id,CorpusVersion.version_no==data.version_no))
 if existing:
  if existing.shard_total!=data.shard_total:raise HTTPException(409,f'版本{data.version_no}已登记，分片总数{existing.shard_total}不可变更')
  return version_state(db,existing),False
 obj=CorpusVersion(corpus_id=corpus_id,version_no=data.version_no,shard_total=data.shard_total,status=VersionStatus.RECEIVING)
 db.add(obj);db.commit()
 record(db,user.email,'version.created',{'corpus_id':corpus_id,'version_no':data.version_no,'shard_total':data.shard_total})
 return version_state(db,obj),True
def _finish(db,version):
 current=active_version(db,version.corpus_id)
 if current and current.version_no>version.version_no:
  version.status=VersionStatus.SUPERSEDED
  return 'version.completed',{'version_id':version.id,'version_no':version.version_no,'active_version_no':current.version_no,'note':'较旧版本收齐，不回滚生效版本'}
 if current:current.status=VersionStatus.SUPERSEDED
 version.status=VersionStatus.ACTIVE
 return 'version.activated',{'version_id':version.id,'version_no':version.version_no,'replaced_version_no':current.version_no if current else None}
def upload_shard(db,version_id,data,user):
 version=db.get(CorpusVersion,version_id)
 if not version:raise HTTPException(404,'版本不存在')
 lock_corpus(db,version.corpus_id);db.refresh(version)
 if version.status==VersionStatus.CONFLICT:raise HTTPException(409,f'版本{version.version_no}已整版隔离，请登记新版本重传')
 if data.shard_index>=version.shard_total:raise HTTPException(422,f'分片序号须为0–{version.shard_total-1}')
 digest=shard_hash(data.documents)
 existing=db.scalar(select(CorpusShard).where(CorpusShard.version_id==version_id,CorpusShard.shard_index==data.shard_index))
 if existing:
  if existing.content_hash==digest:return version_state(db,version),False
  if version.status==VersionStatus.RECEIVING:
   version.status=VersionStatus.CONFLICT;db.commit()
   record(db,user.email,'version.conflict',{'version_id':version_id,'version_no':version.version_no,'shard_index':data.shard_index,'reason':'同片内容冲突'})
  raise HTTPException(409,f'分片{data.shard_index}内容冲突，版本{version.version_no}已整版隔离' if version.status==VersionStatus.CONFLICT else '版本已收齐，分片内容不可变更')
 if version.status!=VersionStatus.RECEIVING:raise HTTPException(409,'版本已收齐，不再接受分片')
 received=db.scalar(select(func.coalesce(func.sum(CorpusShard.document_count),0)).where(CorpusShard.version_id==version_id))
 if received+len(data.documents)>MAX_VERSION_DOCUMENTS:raise HTTPException(422,f'版本展签总数不可超过{MAX_VERSION_DOCUMENTS}篇')
 overlap={r for (r,) in db.execute(select(TokenDocument.reference).where(TokenDocument.version_id==version_id))}&{d.reference for d in data.documents}
 if overlap:raise HTTPException(422,f'展签{sorted(overlap)[0]}等与本版已收分片重复')
 db.add(CorpusShard(version_id=version_id,shard_index=data.shard_index,content_hash=digest,document_count=len(data.documents)))
 db.add_all([TokenDocument(corpus_id=version.corpus_id,version_id=version_id,**d.model_dump()) for d in data.documents])
 try:db.flush()
 except IntegrityError:
  db.rollback();raise HTTPException(409,'分片并发上传冲突，请重试')
 done=db.scalar(select(func.count()).select_from(CorpusShard).where(CorpusShard.version_id==version_id))
 event=_finish(db,version) if done==version.shard_total else None
 db.commit()
 record(db,user.email,'version.shard',{'version_id':version_id,'version_no':version.version_no,'shard_index':data.shard_index,'documents':len(data.documents),'received':done,'shard_total':version.shard_total})
 if event:record(db,user.email,event[0],event[1])
 return version_state(db,version),True
def publish_initial_version(db,corpus,documents):
 version=CorpusVersion(corpus_id=corpus.id,version_no=1,shard_total=1,status=VersionStatus.ACTIVE)
 db.add(version);db.flush()
 db.add(CorpusShard(version_id=version.id,shard_index=0,content_hash=shard_hash(documents),document_count=len(documents)))
 db.add_all([TokenDocument(corpus_id=corpus.id,version_id=version.id,reference=d.reference,title=d.title,tokens_text=d.tokens_text) for d in documents])
 return version
def backfill_versions(db):
 for corpus in db.scalars(select(Corpus)).all():
  if db.scalar(select(CorpusVersion.id).where(CorpusVersion.corpus_id==corpus.id)):continue
  docs=db.scalars(select(TokenDocument).where(TokenDocument.corpus_id==corpus.id,TokenDocument.version_id.is_(None)).order_by(TokenDocument.reference)).all()
  version=publish_initial_version(db,corpus,docs)
  for run in db.scalars(select(TopicRun).where(TopicRun.corpus_id==corpus.id,TopicRun.corpus_version_id.is_(None))):run.corpus_version_id=version.id
  db.commit()
