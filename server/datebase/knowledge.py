from functools import wraps
from contextlib import contextmanager
from server.datebase.base import SessionLocal
from server.datebase.knowledge_class import KnowledgeBaseModel
from server.knowledge_base.utils import KnowledgeFile
from typing import List, Dict
from server.datebase.knowledge_class import KnowledgeFileModel,FileDocModel

@contextmanager
def session_scope():
    """上下文管理器用于自动获取 Session, 避免错误"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def with_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with session_scope() as session:
            try:
                result = f(session, *args, **kwargs)
                session.commit()
                return result
            except:
                session.rollback()
                raise

    return wrapper

@with_session
def add_kb_to_db(session, kb_name, vs_type, embed_model):
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_name).first()
    if not kb:
        kb = KnowledgeBaseModel(kb_name=kb_name, vs_type=vs_type, embed_model=embed_model)
        session.add(kb)
    else: # update kb with new vs_type and embed_model
        kb.vs_type = vs_type
        kb.embed_model = embed_model
    return True


@with_session
def add_file_to_db(session,
                kb_file: KnowledgeFile,
                docs_count: int = 0,
                custom_docs: bool = False,
                doc_infos: List[str] = [], # [{"id": str, "metadata": dict}, ...]
                ):
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_file.kb_name).first()
    if kb:
        # 如果已经存在该文件，则更新文件信息与版本号
        existing_file: KnowledgeFileModel = (session.query(KnowledgeFileModel)
                                             .filter_by(file_name=kb_file.filename,
                                                        kb_name=kb_file.kb_name)
                                            .first())
        mtime = kb_file.get_mtime()
        size = kb_file.get_size()

        if existing_file:
            existing_file.file_mtime = mtime
            existing_file.file_size = size
            existing_file.docs_count = docs_count
            existing_file.custom_docs = custom_docs
            existing_file.file_version += 1
        # 否则，添加新文件
        else:
            new_file = KnowledgeFileModel(
                file_name=kb_file.filename,
                file_ext=kb_file.ext,
                kb_name=kb_file.kb_name,
                document_loader_name=kb_file.document_loader_name,
                text_splitter_name=kb_file.text_splitter_name or "SpacyTextSplitter",
                file_mtime=mtime,
                file_size=size,
                docs_count = docs_count,
                custom_docs=custom_docs,
            )
            kb.file_count += 1
            session.add(new_file)
        add_docs_to_db(kb_name=kb_file.kb_name, file_name=kb_file.filename, doc_infos=doc_infos)
    return True

@with_session
def delete_docs_from_db(session,
                      kb_name: str,
                      file_name: str = None,
                      ) -> List[Dict]:
    '''
    删除某知识库某文件对应的所有Document，并返回被删除的Document。
    返回形式：[{"id": str, "metadata": dict}, ...]
    '''
    docs = list_docs_from_db(kb_name=kb_name, file_name=file_name)
    query = session.query(FileDocModel).filter_by(kb_name=kb_name)
    if file_name:
        query = query.filter_by(file_name=file_name)
    query.delete()
    session.commit()
    return docs

@with_session
def list_docs_from_db(session,
                      kb_name: str,
                      file_name: str = None,
                      metadata: Dict = {},
                      ) -> List[Dict]:
    '''
    列出某知识库某文件对应的所有Document。
    返回形式：[{"id": str, "metadata": dict}, ...]
    '''
    docs = session.query(FileDocModel).filter_by(kb_name=kb_name)
    if file_name:
        docs = docs.filter_by(file_name=file_name)
    for k, v in metadata.items():
        docs = docs.filter(FileDocModel.meta_data[k].as_string()==str(v))

    return [{"id": x.doc_id, "metadata": x.metadata} for x in docs.all()]


@with_session
def delete_file_from_db(session, kb_file: KnowledgeFile):
    existing_file = session.query(KnowledgeFileModel).filter_by(file_name=kb_file.filename,
                                                                kb_name=kb_file.kb_name).first()
    if existing_file:
        session.delete(existing_file)
        delete_docs_from_db(kb_name=kb_file.kb_name, file_name=kb_file.filename)
        session.commit()

        kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_file.kb_name).first()
        if kb:
            kb.file_count -= 1
            session.commit()
    return True

@with_session
def file_exists_in_db(session, kb_file: KnowledgeFile):
    existing_file = session.query(KnowledgeFileModel).filter_by(file_name=kb_file.filename,
                                                                kb_name=kb_file.kb_name).first()
    return True if existing_file else False

@with_session
def list_files_from_db(session, kb_name):
    files = session.query(KnowledgeFileModel).filter_by(kb_name=kb_name).all()
    docs = [f.file_name for f in files]
    return docs

@with_session
def add_docs_to_db(session,
                   kb_name: str,
                   file_name: str,
                   doc_infos: List[Dict]):
    '''
    将某知识库某文件对应的所有Document信息添加到数据库。
    doc_infos形式：[{"id": str, "metadata": dict}, ...]
    '''
    for d in doc_infos:
        obj = FileDocModel(
            kb_name=kb_name,
            file_name=file_name,
            doc_id=d["id"],
            meta_data=d["metadata"],
        )
        session.add(obj)
    return True

@with_session
def delete_files_from_db(session, knowledge_base_name: str):
    session.query(KnowledgeFileModel).filter_by(kb_name=knowledge_base_name).delete()
    session.query(FileDocModel).filter_by(kb_name=knowledge_base_name).delete()
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=knowledge_base_name).first()
    if kb:
        kb.file_count = 0

    session.commit()
    return True

@with_session
def delete_kb_from_db(session, kb_name):
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_name).first()
    if kb:
        session.delete(kb)
    return True

@with_session
def count_files_from_db(session, kb_name: str) -> int:
    return session.query(KnowledgeFileModel).filter_by(kb_name=kb_name).count()

@with_session
def list_kbs_from_db(session, min_file_count: int = -1):
    kbs = session.query(KnowledgeBaseModel.kb_name).filter(KnowledgeBaseModel.file_count > min_file_count).all()
    kbs = [kb[0] for kb in kbs]
    return kbs

@with_session
def kb_exists(session, kb_name):
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_name).first()
    status = True if kb else False
    return status

@with_session
def load_kb_from_db(session, kb_name):
    kb = session.query(KnowledgeBaseModel).filter_by(kb_name=kb_name).first()
    if kb:
        kb_name, vs_type, embed_model = kb.kb_name, kb.vs_type, kb.embed_model
    else:
        kb_name, vs_type, embed_model = None, None, None
    return kb_name, vs_type, embed_model
