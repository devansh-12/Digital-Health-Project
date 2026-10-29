CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE usage_hourly (
    id INTEGER PRIMARY KEY,
    hour_start INTEGER NOT NULL,
    active_s INTEGER DEFAULT 0,
    idle_s INTEGER DEFAULT 0,
    fullscreen_s INTEGER DEFAULT 0,
    call_s INTEGER DEFAULT 0,
    UNIQUE(hour_start)
);

CREATE TABLE breaks (
    id INTEGER PRIMARY KEY,
    due_at INTEGER NOT NULL,
    shown_at INTEGER,
    kind TEXT CHECK(kind IN ('quick', 'long', 'yoga', 'natural')),
    outcome TEXT CHECK(outcome IN ('completed', 'snoozed', 'skipped', 'suppressed', 'expired')),
    duration_s INTEGER
);

CREATE TABLE yoga_sessions (
    id INTEGER PRIMARY KEY,
    started_at INTEGER NOT NULL,
    steps_completed INTEGER,
    total_steps INTEGER,
    duration_s INTEGER
);

CREATE TABLE blink_minutely (
    minute_start INTEGER PRIMARY KEY,
    blinks INTEGER,
    face_present_ratio REAL,
    ear_mean REAL
);

CREATE TABLE daily_scores (
    day TEXT PRIMARY KEY,
    score INTEGER,
    break_c REAL,
    yoga_c REAL,
    screen_c REAL,
    blink_c REAL,
    counted_for_streak INTEGER
);

CREATE TABLE streaks (
    id INTEGER PRIMARY KEY,
    current INTEGER,
    best INTEGER,
    last_counted_day TEXT,
    freeze_week TEXT
);

CREATE TABLE badges (
    code TEXT PRIMARY KEY,
    earned_at INTEGER
);

CREATE TABLE context_rules (
    process TEXT PRIMARY KEY,
    rule TEXT CHECK(rule IN ('allow', 'deny', 'call', 'fullscreen_ok'))
);
