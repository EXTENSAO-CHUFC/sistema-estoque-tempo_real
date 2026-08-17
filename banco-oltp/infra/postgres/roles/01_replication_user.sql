-- AVISO: usuário local de replicação usado pelo Debezium do monorepo.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'debezium_replicator'
    ) THEN
        CREATE ROLE debezium_replicator
        WITH LOGIN REPLICATION PASSWORD 'debezium_password';
    ELSE
        ALTER ROLE debezium_replicator
        WITH LOGIN REPLICATION PASSWORD 'debezium_password';
    END IF;
END
$$;

DO $$
BEGIN
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO debezium_replicator',
        current_database()
    );
END
$$;

GRANT USAGE ON SCHEMA public TO debezium_replicator;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium_replicator;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO debezium_replicator;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO debezium_replicator;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO debezium_replicator;
