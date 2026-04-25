create table if not exists profiles (
  id uuid primary key,
  name text not null,
  email text,
  timezone text not null,
  goals jsonb default '[]'::jsonb,
  preferred_mode text not null,
  date_of_birth date,
  gender text not null default 'prefer_not_to_say',
  sexual_orientation text not null default 'prefer_not_to_say',
  location text,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists sessions (
  id uuid primary key,
  profile_id uuid not null references profiles(id) on delete cascade,
  mode text not null,
  title text,
  summary text,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists messages (
  id uuid primary key,
  session_id uuid not null references sessions(id) on delete cascade,
  role text not null,
  content text not null,
  timestamp timestamptz not null,
  mood_score integer,
  distortion text,
  is_crisis boolean default false
);

create table if not exists mood_logs (
  id uuid primary key,
  session_id uuid not null references sessions(id) on delete cascade,
  profile_id uuid not null references profiles(id) on delete cascade,
  score integer not null,
  note text,
  timestamp timestamptz not null
);

create table if not exists homework (
  id uuid primary key,
  profile_id uuid not null references profiles(id) on delete cascade,
  session_id uuid not null references sessions(id) on delete cascade,
  title text not null,
  instructions text not null,
  status text not null,
  reflection text,
  due_at timestamptz,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists schedules (
  id uuid primary key,
  profile_id uuid not null references profiles(id) on delete cascade,
  title text not null,
  description text,
  start_at timestamptz not null,
  end_at timestamptz not null,
  timezone text not null,
  calendar_url text,
  created_at timestamptz not null
);
