# Database Migrations Guide

## Overview

This project uses Alembic for database schema migrations. The migration system is designed to work with both PostgreSQL (production) and SQLite (local development).

## Migration Structure

### Current Migrations

1. **001_initial_migration** (2025-01-19)
   - Creates all core tables: `users`, `categories`, `transactions`
   - Creates ENUM types for PostgreSQL: `category_type`, `transaction_type`
   - Implements timezone-aware timestamps (TIMESTAMPTZ for PostgreSQL)
   - Creates all necessary indexes including composite indexes for optimization
   - Includes all fields from the current models

### Key Features

#### Tables Created

**users**
- All user profile fields including `monthly_limit`
- Unique constraint on `telegram_id`
- Index on `telegram_id` for fast lookups

**categories**
- Support for both income and expense categories
- Default system categories and user-custom categories
- Composite index on `(user_id, type)` for efficient filtering

**transactions**
- Financial transaction records with decimal precision
- Foreign keys with appropriate CASCADE/RESTRICT rules
- Multiple indexes for query optimization:
  - Single column: `user_id`, `type`, `category_id`, `created_at`
  - Composite: `(user_id, type)`, `(user_id, created_at)`, `(category_id, created_at)`

#### Database-Specific Features

**PostgreSQL**
- Uses native ENUM types for `category_type` and `transaction_type`
- Timezone-aware timestamps (TIMESTAMPTZ)
- Idempotent ENUM creation (won't fail if types already exist)

**SQLite**
- Uses VARCHAR for enum-like fields
- Standard DATETIME for timestamps
- All other features identical to PostgreSQL

## Working with Migrations

### Checking Current Status

```bash
alembic current
```

Shows the current migration revision applied to the database.

### Applying Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade one version forward
alembic upgrade +1

# Upgrade to specific revision
alembic upgrade 001
```

### Rolling Back Migrations

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to base (empty database)
alembic downgrade base

# Downgrade to specific revision
alembic downgrade 001
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description_of_changes"

# Create empty migration for manual editing
alembic revision -m "description_of_changes"
```

### Viewing Migration History

```bash
alembic history --verbose
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's autogenerate is smart but not perfect. Always review generated migrations before applying:

- Check that all intended changes are captured
- Verify no unintended changes are included
- Ensure proper handling of database-specific features

### 2. Test Migrations Locally First

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade base

# Re-apply
alembic upgrade head
```

### 3. Handle Database-Specific Features

When adding PostgreSQL-specific features, always check the dialect:

```python
bind = op.get_bind()
if bind.dialect.name == 'postgresql':
    # PostgreSQL-specific code
    op.execute("CREATE TYPE ...")
```

### 4. Maintain Idempotency

Migrations should be idempotent when possible:

```python
# Good: Won't fail if type already exists
op.execute("""
    DO $$ BEGIN
        CREATE TYPE my_type AS ENUM ('value1', 'value2');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
""")

# Bad: Will fail on re-run
op.execute("CREATE TYPE my_type AS ENUM ('value1', 'value2')")
```

### 5. Use Descriptive Names

Migration file names should clearly describe what they do:
- ✅ `add_user_settings_fields`
- ✅ `create_notification_table`
- ❌ `update_database`
- ❌ `changes`

## Troubleshooting

### "Target database is not up to date"

This error occurs when Alembic thinks the database is behind the migrations:

```bash
# Check current version
alembic current

# If database is actually up to date, stamp it
alembic stamp head

# If database needs migration
alembic upgrade head
```

### Migration Conflicts

If you have conflicting migrations (multiple heads):

```bash
# View all heads
alembic heads

# Merge migrations
alembic merge -m "merge_description" head1 head2
```

### Database Connection Issues

Ensure your `DATABASE_URL` is correctly set:

```bash
# Check environment variable
echo $DATABASE_URL

# For local development, ensure .env file exists
cat .env | grep DATABASE_URL
```

## Production Deployment

### Pre-Deployment Checklist

1. ✅ Test migrations locally with SQLite
2. ✅ Test migrations on staging PostgreSQL
3. ✅ Backup production database
4. ✅ Review migration SQL (use `--sql` flag)
5. ✅ Plan rollback strategy

### Running Migrations in Production

```bash
# SSH into production server
ssh user@production-server

# Navigate to project directory
cd /path/to/project

# Activate virtual environment
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify
alembic current
```

### Docker Deployment

Migrations are automatically run during Docker container startup via the `deploy.sh` script:

```bash
# In deploy.sh
alembic upgrade head
```

To run migrations manually in Docker:

```bash
# Enter container
docker exec -it finance-bot bash

# Run migration
alembic upgrade head
```

## Environment Configuration

### Required Environment Variables

```bash
# PostgreSQL (Production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# SQLite (Local Development)
DATABASE_URL=sqlite+aiosqlite:///./finance.db
```

### Alembic Configuration

The `alembic.ini` file is configured to:
- Use custom file naming with timestamps
- Load DATABASE_URL from environment via `env.py`
- Support both PostgreSQL and SQLite

## Schema Validation

To verify that your models match the database schema:

```bash
# Generate migration to see if there are differences
alembic revision --autogenerate -m "check_schema"

# If output shows "Detected no changes", schema is in sync
# Delete the empty migration file if no changes needed
```

## Migration Dependencies

### Order of Operations

1. **ENUM types** (PostgreSQL only) - Must be created before tables
2. **Tables** - Created in order of dependencies (users → categories → transactions)
3. **Indexes** - Created after tables
4. **Constraints** - Foreign keys created with tables

### Downgrade Order

Reverse of upgrade order:
1. Drop indexes
2. Drop tables (in reverse dependency order)
3. Drop ENUM types

## Common Migration Patterns

### Adding a Column

```python
def upgrade():
    op.add_column('table_name', 
        sa.Column('new_column', sa.String(100), nullable=True)
    )

def downgrade():
    op.drop_column('table_name', 'new_column')
```

### Adding an Index

```python
def upgrade():
    op.create_index('ix_table_column', 'table_name', ['column'])

def downgrade():
    op.drop_index('ix_table_column', table_name='table_name')
```

### Modifying a Column

```python
def upgrade():
    op.alter_column('table_name', 'column_name',
        type_=sa.String(200),
        existing_type=sa.String(100)
    )

def downgrade():
    op.alter_column('table_name', 'column_name',
        type_=sa.String(100),
        existing_type=sa.String(200)
    )
```

## Monitoring and Logging

Alembic logs all operations. To increase verbosity:

```bash
# In alembic.ini, set logger level
[logger_alembic]
level = DEBUG
```

## Backup Strategy

### Before Major Migrations

```bash
# PostgreSQL backup
pg_dump -U user -d dbname > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
cp finance.db finance.db.backup_$(date +%Y%m%d_%H%M%S)
```

### Restore from Backup

```bash
# PostgreSQL restore
psql -U user -d dbname < backup_file.sql

# SQLite restore
cp backup_file.db finance.db
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL ENUM Types](https://www.postgresql.org/docs/current/datatype-enum.html)

