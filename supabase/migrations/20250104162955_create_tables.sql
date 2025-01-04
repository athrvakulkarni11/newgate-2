   -- supabase/migrations/xxxx_create_tables.sql
   CREATE TABLE IF NOT EXISTS organizations (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL UNIQUE,
       description TEXT,
       ideology VARCHAR(255),
       founding_date VARCHAR(255),
       headquarters VARCHAR(255),
       website VARCHAR(255),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE IF NOT EXISTS leaders (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       position VARCHAR(255),
       organization VARCHAR(255) REFERENCES organizations(name),
       background TEXT,
       education TEXT,
       political_history TEXT,
       achievements TEXT,
       source_url TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );