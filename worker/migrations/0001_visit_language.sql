-- UPDATE_32 section 2: the language a creek check's questions were shown in. Run once on a
-- database made before worker/schema.sql had the column, before the Worker that writes it:
--   cd worker && npx wrangler d1 execute second-look --remote --file migrations/0001_visit_language.sql
-- It fails harmlessly with "duplicate column name" if the column is already there. Older rows keep
-- it empty and read as English. The same column as apps/api/migrations/versions/0006.
ALTER TABLE visit ADD COLUMN language TEXT;
