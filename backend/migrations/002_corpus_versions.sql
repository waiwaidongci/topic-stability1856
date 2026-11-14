-- 002_corpus_versions: 展签语料分片版本导入（参考 DDL；运行期由 create_all + ensure_schema 幂等建立）。
-- corpus_versions 承载递增版号与分片总数；status: receiving/active/superseded/conflict。
-- corpus_shards 记录已收分片的内容哈希，同片不同内容即整版隔离。
-- token_documents 归属单一版本，唯一键由 (corpus_id,reference) 改为 (version_id,reference)；
-- 研究运行通过 topic_runs.corpus_version_id 固定读取一个完整版本。
CREATE TABLE corpus_versions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  corpus_id INT NOT NULL REFERENCES corpora(id),
  version_no INT NOT NULL,
  shard_total INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'receiving',
  created_at DATETIME NOT NULL,
  CONSTRAINT uq_corpus_version_no UNIQUE (corpus_id, version_no)
);
CREATE TABLE corpus_shards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  version_id INT NOT NULL REFERENCES corpus_versions(id),
  shard_index INT NOT NULL,
  content_hash VARCHAR(64) NOT NULL,
  document_count INT NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT uq_version_shard_index UNIQUE (version_id, shard_index)
);
ALTER TABLE token_documents ADD COLUMN version_id INT NULL REFERENCES corpus_versions(id);
ALTER TABLE token_documents ADD INDEX idx_tokdoc_corpus (corpus_id);
ALTER TABLE token_documents DROP INDEX corpus_id;
ALTER TABLE token_documents ADD CONSTRAINT uq_version_reference UNIQUE (version_id, reference);
ALTER TABLE topic_runs ADD COLUMN corpus_version_id INT NULL REFERENCES corpus_versions(id);
