// Critical PostgreSQL Extensions Configuration
// This file contains the list of critical extensions to check for in PostgreSQL tests
// Update this list as needed to track additional extensions

const CRITICAL_POSTGRESQL_EXTENSIONS = [
    {
        name: 'timescaledb',
        displayName: 'TimescaleDB',
        description: 'Time-series database extension',
        category: 'Analytics'
    },
    {
        name: 'vector',
        displayName: 'pgvector',
        description: 'Vector similarity search',
        category: 'AI/ML'
    },
    {
        name: 'pgcrypto',
        displayName: 'pgcrypto',
        description: 'Cryptographic functions',
        category: 'Security'
    },
    {
        name: 'uuid-ossp',
        displayName: 'uuid-ossp',
        description: 'UUID generation',
        category: 'Data Types'
    },
    {
        name: 'postgis',
        displayName: 'PostGIS',
        description: 'Geographic objects support',
        category: 'Geospatial'
    },
    {
        name: 'pg_trgm',
        displayName: 'pg_trgm',
        description: 'Trigram matching for similarity searches',
        category: 'Search'
    },
    {
        name: 'fuzzystrmatch',
        displayName: 'fuzzystrmatch',
        description: 'Fuzzy string matching',
        category: 'Search'
    },
    {
        name: 'age',
        displayName: 'Apache AGE',
        description: 'Graph database extension',
        category: 'Graph'
    },
    {
        name: 'unaccent',
        displayName: 'unaccent',
        description: 'Text search dictionary for removing accents',
        category: 'Search'
    },
    {
        name: 'pg_cron',
        displayName: 'pg_cron',
        description: 'Job scheduler',
        category: 'Automation'
    }
];

// Export for use in dashboard
if (typeof window !== 'undefined') {
    window.CRITICAL_POSTGRESQL_EXTENSIONS = CRITICAL_POSTGRESQL_EXTENSIONS;
}
