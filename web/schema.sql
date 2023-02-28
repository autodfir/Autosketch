CREATE TABLE user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);


CREATE TABLE task (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES user(id),
  date TEXT NOT NULL,
  sketch TEXT NOT NULL,
  timeline TEXT NOT NULL,
  task_type TEXT NOT NULL
);