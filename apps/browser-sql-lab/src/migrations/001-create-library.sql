CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  published_year INTEGER NOT NULL CHECK (published_year > 0),
  rating REAL NOT NULL CHECK (rating >= 0 AND rating <= 5),
  added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS books_author_idx ON books(author);
