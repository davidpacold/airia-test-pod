# Static Assets

This directory contains static files served by the application.

## Files

### `style.css`
Main stylesheet for the dashboard UI.

### `critical-extensions.js`
Configuration file containing the list of critical PostgreSQL extensions to check.

## Updating Critical PostgreSQL Extensions

To add, remove, or modify the list of critical PostgreSQL extensions displayed in the test results:

1. Edit `critical-extensions.js`
2. Add/remove/modify entries in the `CRITICAL_POSTGRESQL_EXTENSIONS` array

### Extension Object Structure

```javascript
{
    name: 'extension_name',           // PostgreSQL extension name (lowercase)
    displayName: 'Display Name',      // Human-readable name shown in UI
    description: 'Short description', // Brief description of functionality
    category: 'Category'              // Category: Analytics, AI/ML, Security, etc.
}
```

### Example: Adding a New Extension

```javascript
{
    name: 'pg_stat_statements',
    displayName: 'pg_stat_statements',
    description: 'Track SQL statement execution statistics',
    category: 'Performance'
}
```

### Categories

Use these standard categories for consistency:
- **Analytics** - Time-series, analytics extensions
- **AI/ML** - Machine learning, vector search
- **Security** - Cryptography, authentication
- **Data Types** - UUID, JSON, specialized types
- **Geospatial** - Geographic data support
- **Search** - Full-text search, fuzzy matching
- **Graph** - Graph database functionality
- **Automation** - Job scheduling, triggers
- **Performance** - Monitoring, optimization

### Testing Changes

After modifying the file:
1. Rebuild the Docker image
2. Redeploy the test pod
3. Run the PostgreSQL test to see the updated extension status

The extension status will show:
- ✅ **Installed** - Extension is enabled in the database
- ⚠️ **Available** - Extension is available but not enabled (can be installed with `CREATE EXTENSION`)
- ❌ **Not Available** - Extension is not available in this PostgreSQL installation
