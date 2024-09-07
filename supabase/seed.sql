CREATE TABLE IF NOT EXISTS "ChatHistory" (
    "id" SERIAL PRIMARY KEY,
    "session_id" INT NOT NULL,
    "user_id" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "role" TEXT NOT NULL
);