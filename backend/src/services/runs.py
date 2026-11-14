from sqlalchemy import select
from fastapi import HTTPException
from src.models import Corpus,CorpusVersion,TopicRun
from src.constants.enums import RunStatus,VersionStatus
from src.utils.serialize import row
from .audit import record
def list_runs(db):
 runs=db.scalars(select(TopicRun).order_by(TopicRun.id.desc())).all()
 versions={v.id:v.version_no for v in db.scalars(select(CorpusVersion))}
 return [dict(row(r),version_no=versions.get(r.corpus_version_id)) for r in runs]
def get_run(db,id):
 obj=db.get(TopicRun,id)
 if not obj:raise HTTPException(404,'主题运行不存在')
 return obj
def create_run(db,data,user):
 if not db.get(Corpus,data.corpus_id):raise HTTPException(404,'语料不存在')
 version=db.scalar(select(CorpusVersion).where(CorpusVersion.corpus_id==data.corpus_id,CorpusVersion.status==VersionStatus.ACTIVE))
 if not version:raise HTTPException(409,'语料尚无收齐生效的版本，请先完成分片导入')
 obj=TopicRun(corpus_id=data.corpus_id,corpus_version_id=version.id,name=data.name,config=data.model_dump(exclude={'name','corpus_id'}),creator_id=user.id);db.add(obj);db.commit()
 from src.worker import analyze_run
 try:analyze_run.delay(obj.id)
 except Exception:obj.status=RunStatus.FAILED;obj.error='队列不可用';db.commit();raise HTTPException(503,obj.error)
 record(db,user.email,'topic.queued',{'run_id':obj.id,'version_no':version.version_no});return row(obj)
