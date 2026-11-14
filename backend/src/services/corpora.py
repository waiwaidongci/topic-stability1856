from sqlalchemy import select,func
from fastapi import HTTPException
from src.models import Corpus,TokenDocument,CorpusVersion
from src.constants.enums import VersionStatus
from src.utils.serialize import row
from .audit import record
from .versions import publish_initial_version
def list_corpora(db):
 result=[]
 for c in db.scalars(select(Corpus).order_by(Corpus.id)):
  active=db.scalar(select(CorpusVersion).where(CorpusVersion.corpus_id==c.id,CorpusVersion.status==VersionStatus.ACTIVE))
  count=db.scalar(select(func.count()).select_from(TokenDocument).where(TokenDocument.version_id==active.id)) if active else 0
  result.append(dict(row(c),document_count=count,active_version_no=active.version_no if active else None))
 return result
def list_documents(db,corpus_id=None,version_id=None):
 q=select(TokenDocument).order_by(TokenDocument.reference)
 if version_id is not None:q=q.where(TokenDocument.version_id==version_id)
 else:
  q=q.join(CorpusVersion,TokenDocument.version_id==CorpusVersion.id).where(CorpusVersion.status==VersionStatus.ACTIVE)
  if corpus_id is not None:q=q.where(TokenDocument.corpus_id==corpus_id)
 return [row(x) for x in db.scalars(q)]
def create_corpus(db,data,user):
 if db.scalar(select(Corpus).where(Corpus.name==data.name)):raise HTTPException(409,'语料名称已存在')
 obj=Corpus(**data.model_dump(exclude={'documents'}));db.add(obj);db.flush()
 version=publish_initial_version(db,obj,data.documents);db.commit()
 record(db,user.email,'corpus.import',{'corpus_id':obj.id,'version_no':version.version_no,'documents':len(data.documents)});return row(obj)
def patch_document(db,id,data,user):
 obj=db.get(TokenDocument,id)
 if not obj:raise HTTPException(404,'文档不存在')
 obj.title=data.title;obj.tokens_text=data.tokens_text;db.commit();record(db,user.email,'document.edit',{'document_id':id});return row(obj)
