CREATE TABLE IF NOT EXISTS cloud_logs (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    "user"          TEXT NOT NULL,
    action          TEXT NOT NULL,
    source_ip       TEXT,
    region          TEXT,
    cloud_service   TEXT,
    severity        TEXT CHECK(severity IN ('Critical','High','Medium','Low')),
    is_malicious    INTEGER DEFAULT 0 CHECK(is_malicious IN (0,1)),
    scenario_id     INTEGER DEFAULT 0,
    mitre_technique TEXT DEFAULT '',
    mitre_tactic    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS logs (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    "user"          TEXT,
    event           TEXT,
    source          TEXT,
    ip              TEXT,
    region          TEXT,
    user_agent      TEXT,
    status          TEXT,
    error_code      TEXT,
    resource        TEXT,
    raw_data        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL PRIMARY KEY,
    type            TEXT NOT NULL CHECK(type IN ('IOA','IOM')),
    severity        TEXT NOT NULL CHECK(severity IN ('Critical','High','Medium','Low')),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    status          TEXT DEFAULT 'Open' CHECK(status IN ('Open','Resolved')),
    related_log_id  BIGINT REFERENCES cloud_logs(id),
    best_practice   INTEGER DEFAULT 0,
    mitre_technique TEXT DEFAULT '',
    mitre_tactic    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS attack_scenarios (
    id                      INTEGER PRIMARY KEY,
    name                    TEXT NOT NULL,
    description             TEXT NOT NULL,
    attack_vector           TEXT NOT NULL,
    layer_targeted          TEXT NOT NULL,
    best_practice_violated  TEXT NOT NULL,
    mitre_tactics           TEXT NOT NULL
);
