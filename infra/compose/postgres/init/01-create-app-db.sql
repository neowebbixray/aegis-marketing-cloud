DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'amc') THEN
        CREATE ROLE amc WITH LOGIN PASSWORD 'amc_secret';
    END IF;
END $$;

-- Create the application database if it doesn't exist
SELECT 'CREATE DATABASE aegis_marketing_cloud OWNER amc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aegis_marketing_cloud')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE aegis_marketing_cloud TO amc;
