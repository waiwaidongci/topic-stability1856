from fastapi import APIRouter,Depends,Response
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.schemas.corpus import CorpusInput,DocumentPatch,VersionInput,ShardInput
from src.services import corpora,versions
from src.constants.vocabulary import WHITELIST
router=APIRouter()
@router.get('/corpora')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return corpora.list_corpora(db)
@router.post('/corpora',status_code=201)
def create(data:CorpusInput,db:Session=Depends(get_db),user=Depends(writers)):return corpora.create_corpus(db,data,user)
@router.get('/corpora/{corpus_id}/versions')
def version_index(corpus_id:int,db:Session=Depends(get_db),user=Depends(current_user)):return versions.list_versions(db,corpus_id)
@router.post('/corpora/{corpus_id}/versions')
def version_create(corpus_id:int,data:VersionInput,response:Response,db:Session=Depends(get_db),user=Depends(writers)):
 state,created=versions.create_version(db,corpus_id,data,user)
 response.status_code=201 if created else 200
 return state
@router.post('/versions/{version_id}/shards')
def shard_upload(version_id:int,data:ShardInput,response:Response,db:Session=Depends(get_db),user=Depends(writers)):
 state,accepted=versions.upload_shard(db,version_id,data,user)
 response.status_code=201 if accepted else 200
 return state
@router.get('/documents')
def documents(db:Session=Depends(get_db),user=Depends(current_user)):return corpora.list_documents(db)
@router.patch('/documents/{id}')
def document(id:int,data:DocumentPatch,db:Session=Depends(get_db),user=Depends(writers)):return corpora.patch_document(db,id,data,user)
@router.get('/whitelist')
def whitelist(user=Depends(current_user)):return list(WHITELIST)
