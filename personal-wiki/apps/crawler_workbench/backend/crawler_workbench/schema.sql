create table if not exists source_profiles (
  id text primary key,
  name text not null,
  type text not null check (type in ('web', 'rss', 'github', 'arxiv')),
  target_domain text not null,
  url text not null,
  trust_level text not null check (trust_level in ('trusted', 'untrusted')),
  schedule text not null,
  auto_ingest integer not null default 0,
  auth_required integer not null default 0,
  baseline_on_first_run integer not null default 0,
  run_policy text not null default 'scheduled' check (run_policy in ('scheduled', 'once')),
  auth_state text not null default 'ready',
  auth_method text,
  auth_ref text,
  config_json text not null default '{}',
  topic text not null,
  enabled integer not null default 1,
  last_run_at text,
  next_run_at text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
);

create table if not exists source_auth_refs (
  source_id text primary key references source_profiles(id) on delete cascade,
  auth_method text not null,
  auth_ref text not null,
  state text not null,
  updated_at text not null default current_timestamp
);

create table if not exists fetch_runs (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  status text not null,
  started_at text not null default current_timestamp,
  finished_at text,
  fetched_count integer not null default 0,
  changed_count integer not null default 0,
  skipped_count integer not null default 0,
  error text
);

create table if not exists raw_items (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  fetch_run_id integer references fetch_runs(id) on delete set null,
  target_domain text not null,
  canonical_url text not null,
  raw_path text not null,
  title text not null,
  content_hash text not null,
  content_bytes integer not null,
  metadata_json text not null,
  created_at text not null default current_timestamp
);

create table if not exists content_versions (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  canonical_url text not null,
  content_hash text not null,
  etag text,
  last_modified text,
  raw_item_id integer references raw_items(id) on delete set null,
  created_at text not null default current_timestamp,
  unique(source_id, canonical_url, content_hash)
);

create table if not exists accelerator_candidates (
  id integer primary key autoincrement,
  vendor text not null,
  model_name text not null,
  normalized_model text not null,
  scope text not null,
  source_profile_id text not null references source_profiles(id) on delete cascade,
  source_url text not null,
  evidence_url text,
  evidence_text text not null,
  confidence real not null,
  status text not null default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  accepted_source_id text references source_profiles(id) on delete set null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  unique(vendor, normalized_model, evidence_url)
);

create unique index if not exists accelerator_candidates_effective_evidence_url_idx
on accelerator_candidates(vendor, normalized_model, coalesce(evidence_url, source_url));

create table if not exists ingest_tasks (
  id integer primary key autoincrement,
  source_id text not null references source_profiles(id) on delete cascade,
  raw_item_id integer references raw_items(id) on delete set null,
  target_domain text not null,
  status text not null,
  risk_level text not null,
  reason text not null,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp,
  codex_job_id integer,
  validation_run_id integer,
  commit_id integer
);

create table if not exists codex_jobs (
  id integer primary key autoincrement,
  job_type text not null,
  target_domain text,
  prompt text not null,
  status text not null,
  stdout text not null default '',
  stderr text not null default '',
  exit_code integer,
  created_at text not null default current_timestamp,
  started_at text,
  finished_at text
);

create table if not exists validation_runs (
  id integer primary key autoincrement,
  target_domain text,
  status text not null,
  command text not null,
  output text not null default '',
  created_at text not null default current_timestamp
);

create table if not exists commit_records (
  id integer primary key autoincrement,
  source_id text,
  target_domain text not null,
  commit_sha text not null,
  message text not null,
  created_at text not null default current_timestamp
);

create virtual table if not exists wiki_search_fts using fts5(
  path,
  domain,
  title,
  description,
  body,
  source_refs,
  raw_metadata
);
