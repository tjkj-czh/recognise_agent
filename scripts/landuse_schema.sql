-- 用地识别智能体数据库初始化脚本
-- 适配: PostgreSQL 16 + PostGIS 3.4

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- 1) 用户与权限（RBAC）
-- =========================
CREATE TABLE IF NOT EXISTS t_user (
  user_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username           VARCHAR(64) NOT NULL UNIQUE,
  display_name       VARCHAR(64) NOT NULL,
  email              VARCHAR(128),
  password_hash      VARCHAR(255) NOT NULL,
  status             VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_role (
  role_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_code          VARCHAR(32) NOT NULL UNIQUE, -- viewer/operator/reviewer/admin
  role_name          VARCHAR(64) NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_user_role (
  user_id            UUID NOT NULL REFERENCES t_user(user_id) ON DELETE CASCADE,
  role_id            UUID NOT NULL REFERENCES t_role(role_id) ON DELETE CASCADE,
  assigned_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id)
);

-- =========================
-- 2) 项目与任务编排
-- =========================
CREATE TABLE IF NOT EXISTS t_project (
  project_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_code       VARCHAR(64) NOT NULL UNIQUE,
  project_name       VARCHAR(128) NOT NULL,
  region_name        VARCHAR(128),
  status             VARCHAR(16) NOT NULL DEFAULT 'active',
  owner_user_id      UUID REFERENCES t_user(user_id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_task (
  task_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id         UUID NOT NULL REFERENCES t_project(project_id) ON DELETE CASCADE,
  task_name          VARCHAR(128) NOT NULL,
  trace_id           VARCHAR(64) NOT NULL,
  idempotency_key    VARCHAR(128),
  status             VARCHAR(24) NOT NULL DEFAULT 'pending', -- pending/running/success/failed/cancelled
  progress_pct       NUMERIC(5,2) NOT NULL DEFAULT 0,
  retry_count        INT NOT NULL DEFAULT 0,
  error_message      TEXT,
  started_at         TIMESTAMPTZ,
  finished_at        TIMESTAMPTZ,
  created_by         UUID REFERENCES t_user(user_id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (project_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_t_task_project_status ON t_task(project_id, status);
CREATE INDEX IF NOT EXISTS idx_t_task_trace_id ON t_task(trace_id);

-- =========================
-- 3) 影像与图斑底座
-- =========================
CREATE TABLE IF NOT EXISTS t_image (
  image_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id                UUID NOT NULL REFERENCES t_task(task_id) ON DELETE CASCADE,
  image_code             VARCHAR(64) NOT NULL UNIQUE,
  object_key             VARCHAR(512) NOT NULL, -- MinIO key
  image_type             VARCHAR(32),
  resolution             NUMERIC(10,3),
  capture_date           DATE,
  coordinate_system      VARCHAR(64) NOT NULL DEFAULT 'CGCS2000',
  bbox_minx              NUMERIC(15,6),
  bbox_miny              NUMERIC(15,6),
  bbox_maxx              NUMERIC(15,6),
  bbox_maxy              NUMERIC(15,6),
  rows                   INT,
  cols                   INT,
  bands                  INT,
  file_size_mb           NUMERIC(12,3),
  source                 VARCHAR(128),
  status                 VARCHAR(16) NOT NULL DEFAULT 'pending',
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_image_task_id ON t_image(task_id);
CREATE INDEX IF NOT EXISTS idx_t_image_status ON t_image(status);

CREATE TABLE IF NOT EXISTS t_patch (
  patch_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  image_id               UUID NOT NULL REFERENCES t_image(image_id) ON DELETE CASCADE,
  patch_code             VARCHAR(64) NOT NULL UNIQUE,
  geometry               GEOMETRY(MultiPolygon, 4490) NOT NULL,
  area_sqm               NUMERIC(16,4) NOT NULL,
  perimeter_m            NUMERIC(16,4),
  centroid               GEOMETRY(Point, 4490),
  slice_index            VARCHAR(64),
  min_mapping_area       NUMERIC(16,4),
  is_edge_patch          BOOLEAN NOT NULL DEFAULT FALSE,
  fragmentation_index    NUMERIC(6,4),
  quality_label          VARCHAR(16), -- 优质/可用/存疑/低质
  quality_score          NUMERIC(5,4),
  quality_issues         JSONB,       -- ["边缘模糊", ...]
  is_low_quality_area    BOOLEAN NOT NULL DEFAULT FALSE,
  low_quality_area_desc  TEXT,
  preprocessing_note     TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_patch_image_id ON t_patch(image_id);
CREATE INDEX IF NOT EXISTS idx_t_patch_quality_label ON t_patch(quality_label);
CREATE INDEX IF NOT EXISTS idx_t_patch_low_quality ON t_patch(is_low_quality_area);
CREATE INDEX IF NOT EXISTS idx_t_patch_geom_gist ON t_patch USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_t_patch_centroid_gist ON t_patch USING GIST(centroid);

-- =========================
-- 4) 分类体系与映射
-- =========================
CREATE TABLE IF NOT EXISTS t_classification_system (
  class_id               VARCHAR(32) PRIMARY KEY,
  class_level1           VARCHAR(64) NOT NULL,
  class_level2           VARCHAR(64),
  class_level3           VARCHAR(64),
  is_key_class           BOOLEAN NOT NULL DEFAULT FALSE,
  description            TEXT,
  gb_code                VARCHAR(32),
  min_mapping_area       NUMERIC(16,4),
  display_color          VARCHAR(16),
  status                 VARCHAR(16) NOT NULL DEFAULT 'enabled',
  data_version           VARCHAR(16) NOT NULL DEFAULT 'v1.0',
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_label_mapping (
  mapping_id             BIGSERIAL PRIMARY KEY,
  model_name             VARCHAR(64) NOT NULL,
  model_version          VARCHAR(32),
  model_raw_label        VARCHAR(64) NOT NULL,
  target_class_id        VARCHAR(32) NOT NULL REFERENCES t_classification_system(class_id),
  is_ambiguous           BOOLEAN NOT NULL DEFAULT FALSE,
  ambiguous_with         VARCHAR(128),
  mapping_confidence     NUMERIC(5,4) NOT NULL DEFAULT 1.0,
  needs_manual_confirm   BOOLEAN NOT NULL DEFAULT FALSE,
  data_version           VARCHAR(16) NOT NULL DEFAULT 'v1.0',
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (model_name, model_version, model_raw_label, data_version)
);

CREATE INDEX IF NOT EXISTS idx_t_label_mapping_target_class ON t_label_mapping(target_class_id);

CREATE TABLE IF NOT EXISTS t_confidence_threshold (
  config_id              BIGSERIAL PRIMARY KEY,
  class_id               VARCHAR(32) NOT NULL REFERENCES t_classification_system(class_id),
  high_confidence_min    NUMERIC(5,4) NOT NULL,
  medium_confidence_min  NUMERIC(5,4) NOT NULL,
  low_confidence_max     NUMERIC(5,4) NOT NULL,
  mixed_threshold        NUMERIC(6,4) NOT NULL,
  is_class_specific      BOOLEAN NOT NULL DEFAULT TRUE,
  data_version           VARCHAR(16) NOT NULL DEFAULT 'v1.0',
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (high_confidence_min >= medium_confidence_min),
  CHECK (medium_confidence_min >= low_confidence_max)
);

CREATE INDEX IF NOT EXISTS idx_t_conf_threshold_class_ver ON t_confidence_threshold(class_id, data_version);

-- =========================
-- 5) 多模型识别与验证链路
-- =========================
CREATE TABLE IF NOT EXISTS t_patch_model_prediction (
  prediction_id          BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  model_name             VARCHAR(64) NOT NULL,
  model_version          VARCHAR(32) NOT NULL,
  raw_label              VARCHAR(64) NOT NULL,
  mapped_class_id        VARCHAR(32) REFERENCES t_classification_system(class_id),
  confidence             NUMERIC(5,4),
  rank_in_model          INT,
  evidence               JSONB,
  predicted_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_pred_patch ON t_patch_model_prediction(patch_id);
CREATE INDEX IF NOT EXISTS idx_t_pred_model ON t_patch_model_prediction(model_name, model_version);

CREATE TABLE IF NOT EXISTS t_patch_vote (
  vote_id                BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL UNIQUE REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  vote_status            VARCHAR(16) NOT NULL, -- unanimous/majority/disputed
  candidate_classes      JSONB NOT NULL,
  winner_class_id        VARCHAR(32) REFERENCES t_classification_system(class_id),
  vote_reason            TEXT,
  voted_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_patch_vote_status ON t_patch_vote(vote_status);

CREATE TABLE IF NOT EXISTS t_patch_vlm_judgement (
  vlm_id                 BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL UNIQUE REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  triggered_by_vote      BOOLEAN NOT NULL DEFAULT TRUE,
  prompt_version         VARCHAR(32) NOT NULL,
  candidate_classes      JSONB,
  judge_class_id         VARCHAR(32) REFERENCES t_classification_system(class_id),
  judge_confidence       NUMERIC(5,4),
  judge_reason           TEXT,
  is_timeout             BOOLEAN NOT NULL DEFAULT FALSE,
  is_fallback            BOOLEAN NOT NULL DEFAULT FALSE,
  judged_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS t_patch_classification (
  result_id              BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL UNIQUE REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  dominant_class_id      VARCHAR(32) REFERENCES t_classification_system(class_id),
  dominant_area_ratio    NUMERIC(6,4),
  dominant_confidence    NUMERIC(5,4),
  is_mixed               BOOLEAN NOT NULL DEFAULT FALSE,
  mixed_label            VARCHAR(128),
  mixed_note             TEXT,
  is_hard_to_judge       BOOLEAN NOT NULL DEFAULT FALSE,
  hard_to_judge_reason   TEXT,
  overall_confidence     NUMERIC(5,4),
  verify_status          VARCHAR(24) NOT NULL DEFAULT 'pending', -- pending/verified/suspected
  quality_note           VARCHAR(64),
  model_version          VARCHAR(32),
  rule_version           VARCHAR(32),
  data_version           VARCHAR(16),
  trace_id               VARCHAR(64),
  classified_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_patch_cls_dom ON t_patch_classification(dominant_class_id);
CREATE INDEX IF NOT EXISTS idx_t_patch_cls_flags ON t_patch_classification(is_mixed, is_hard_to_judge, verify_status);

CREATE TABLE IF NOT EXISTS t_patch_class_breakdown (
  breakdown_id           BIGSERIAL PRIMARY KEY,
  result_id              BIGINT NOT NULL REFERENCES t_patch_classification(result_id) ON DELETE CASCADE,
  patch_id               UUID NOT NULL REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  class_id               VARCHAR(32) NOT NULL REFERENCES t_classification_system(class_id),
  area_ratio             NUMERIC(6,4) NOT NULL,
  area_sqm               NUMERIC(16,4),
  confidence             NUMERIC(5,4),
  rank_in_patch          INT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (result_id, class_id)
);

CREATE INDEX IF NOT EXISTS idx_t_breakdown_patch ON t_patch_class_breakdown(patch_id);
CREATE INDEX IF NOT EXISTS idx_t_breakdown_class ON t_patch_class_breakdown(class_id);

CREATE TABLE IF NOT EXISTS t_low_confidence_area (
  lca_id                 BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  result_id              BIGINT NOT NULL REFERENCES t_patch_classification(result_id) ON DELETE CASCADE,
  location_desc          VARCHAR(128),
  geometry               GEOMETRY(MultiPolygon, 4490) NOT NULL,
  area_sqm               NUMERIC(16,4),
  reason                 VARCHAR(64),
  confidence             NUMERIC(5,4),
  suggestion             VARCHAR(128),
  is_upstream_quality_issue BOOLEAN NOT NULL DEFAULT FALSE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_lca_patch ON t_low_confidence_area(patch_id);
CREATE INDEX IF NOT EXISTS idx_t_lca_reason ON t_low_confidence_area(reason);
CREATE INDEX IF NOT EXISTS idx_t_lca_geom_gist ON t_low_confidence_area USING GIST(geometry);

-- =========================
-- 6) 规则与合规提示
-- =========================
CREATE TABLE IF NOT EXISTS t_compliance_rule (
  rule_id                BIGSERIAL PRIMARY KEY,
  rule_code              VARCHAR(64) NOT NULL UNIQUE,
  rule_name              VARCHAR(128) NOT NULL,
  rule_category          VARCHAR(32) NOT NULL,
  trigger_class_id       VARCHAR(32) REFERENCES t_classification_system(class_id),
  trigger_condition      TEXT,
  trigger_area_ratio_min NUMERIC(6,4),
  trigger_area_sqm_min   NUMERIC(16,4),
  prompt_level           VARCHAR(24) NOT NULL, -- auto_prompt/focus_prompt/manual_review
  prompt_template        TEXT NOT NULL,
  is_auto_prompt         BOOLEAN NOT NULL DEFAULT FALSE,
  can_auto_conclude      BOOLEAN NOT NULL DEFAULT FALSE,
  priority               INT NOT NULL DEFAULT 5,
  status                 VARCHAR(16) NOT NULL DEFAULT 'enabled',
  rule_version           VARCHAR(16) NOT NULL DEFAULT 'v1.0',
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_rule_category ON t_compliance_rule(rule_category, prompt_level);

CREATE TABLE IF NOT EXISTS t_compliance_prompt (
  prompt_id              BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  result_id              BIGINT NOT NULL REFERENCES t_patch_classification(result_id) ON DELETE CASCADE,
  rule_id                BIGINT NOT NULL REFERENCES t_compliance_rule(rule_id),
  prompt_level           VARCHAR(24) NOT NULL,
  prompt_content         TEXT NOT NULL,
  risk_type              VARCHAR(64),
  needs_manual_review    BOOLEAN NOT NULL DEFAULT FALSE,
  review_priority        INT,
  review_reason          TEXT,
  is_conclusion          BOOLEAN NOT NULL DEFAULT FALSE,
  agent_version          VARCHAR(16),
  trace_id               VARCHAR(64),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_prompt_patch ON t_compliance_prompt(patch_id);
CREATE INDEX IF NOT EXISTS idx_t_prompt_rule_level ON t_compliance_prompt(rule_id, prompt_level);
CREATE INDEX IF NOT EXISTS idx_t_prompt_manual_review ON t_compliance_prompt(needs_manual_review, review_priority);

CREATE TABLE IF NOT EXISTS t_patch_summary (
  summary_id             BIGSERIAL PRIMARY KEY,
  patch_id               UUID NOT NULL UNIQUE REFERENCES t_patch(patch_id) ON DELETE CASCADE,
  dominant_class_id      VARCHAR(32) REFERENCES t_classification_system(class_id),
  dominant_area_ratio    NUMERIC(6,4),
  overall_confidence     NUMERIC(5,4),
  is_mixed               BOOLEAN NOT NULL DEFAULT FALSE,
  mixed_label            VARCHAR(128),
  risk_count             INT NOT NULL DEFAULT 0,
  highest_risk_type      VARCHAR(64),
  needs_review           BOOLEAN NOT NULL DEFAULT FALSE,
  review_priority        INT,
  summary_text           TEXT,
  generated_by           VARCHAR(32) DEFAULT 'compliance-agent',
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_summary_review ON t_patch_summary(needs_review, review_priority);

-- =========================
-- 7) 评测、日志、审计
-- =========================
CREATE TABLE IF NOT EXISTS t_eval_sample (
  sample_id              BIGSERIAL PRIMARY KEY,
  sample_code            VARCHAR(64) NOT NULL UNIQUE,
  sample_type            VARCHAR(16) NOT NULL, -- 标准/边界/异常/对抗/鲁棒性
  owner_name             VARCHAR(32),
  patch_id               UUID REFERENCES t_patch(patch_id),
  description            TEXT,
  input_data             JSONB,
  expected_output        JSONB,
  actual_output          JSONB,
  is_passed              BOOLEAN,
  failure_reason         TEXT,
  error_type             VARCHAR(64),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_eval_owner_type ON t_eval_sample(owner_name, sample_type);

CREATE TABLE IF NOT EXISTS t_agent_log (
  log_id                 BIGSERIAL PRIMARY KEY,
  task_id                UUID REFERENCES t_task(task_id) ON DELETE SET NULL,
  trace_id               VARCHAR(64),
  agent_name             VARCHAR(64) NOT NULL,
  agent_version          VARCHAR(32),
  skill_name             VARCHAR(128),
  patch_id               UUID REFERENCES t_patch(patch_id) ON DELETE SET NULL,
  input_summary          TEXT,
  output_summary         TEXT,
  is_success             BOOLEAN NOT NULL,
  error_message          TEXT,
  duration_ms            INT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_agent_log_trace ON t_agent_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_t_agent_log_agent_time ON t_agent_log(agent_name, created_at DESC);

CREATE TABLE IF NOT EXISTS t_error_registry (
  error_id               BIGSERIAL PRIMARY KEY,
  agent_name             VARCHAR(64) NOT NULL,
  error_type             VARCHAR(64) NOT NULL,
  error_desc             TEXT NOT NULL,
  severity               VARCHAR(16) NOT NULL, -- high/medium/low
  occurrence_count       INT NOT NULL DEFAULT 1,
  sample_codes           TEXT,
  root_cause             TEXT,
  fix_status             VARCHAR(16) NOT NULL DEFAULT 'open', -- open/fixed/wont_fix
  fix_version            VARCHAR(32),
  fix_note               TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_error_registry_status ON t_error_registry(fix_status, severity);

CREATE TABLE IF NOT EXISTS t_audit_log (
  audit_id               BIGSERIAL PRIMARY KEY,
  user_id                UUID REFERENCES t_user(user_id),
  task_id                UUID REFERENCES t_task(task_id),
  trace_id               VARCHAR(64),
  action                 VARCHAR(128) NOT NULL,
  resource_type          VARCHAR(64),
  resource_id            VARCHAR(128),
  request_payload        JSONB,
  response_payload       JSONB,
  ip_address             VARCHAR(64),
  user_agent             VARCHAR(255),
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_t_audit_trace ON t_audit_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_t_audit_user_time ON t_audit_log(user_id, created_at DESC);

COMMIT;
