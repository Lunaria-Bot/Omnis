CREATE TABLE IF NOT EXISTS guild_config (
  guild_id BIGINT PRIMARY KEY,
  log_channel_id BIGINT,
  ticket_category_id BIGINT,
  staff_role_id BIGINT
);

CREATE TABLE IF NOT EXISTS moderation_cases (
  id BIGSERIAL PRIMARY KEY,
  guild_id BIGINT NOT NULL,
  target_id BIGINT NOT NULL,
  moderator_id BIGINT NOT NULL,
  action TEXT NOT NULL,        -- warn, kick, ban
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tickets (
  id BIGSERIAL PRIMARY KEY,
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  channel_id BIGINT UNIQUE NOT NULL,
  status TEXT NOT NULL,        -- open, closed
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  guild_id BIGINT NOT NULL,
  event_type TEXT NOT NULL,    -- message_delete, member_join, member_leave
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
