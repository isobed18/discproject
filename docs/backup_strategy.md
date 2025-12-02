# Backup Strategy

## Persistent Volumes
- **PostgreSQL**: `postgres_data` volume mapped to `/var/lib/postgresql/data`.
- **Redis**: `redis_data` volume mapped to `/data`.
- **Vault**: `vault_data` volume (if persistent).

## Backup Procedures

### PostgreSQL
- **Tool**: `pg_dump` or `wal-g`.
- **Frequency**: Daily full backups, continuous WAL archiving.
- **Storage**: S3 bucket (encrypted).
- **Retention**: 30 days.

### Redis
- **Persistence**: RDB snapshots (every 15 mins) + AOF (every second).
- **Backup**: Copy `dump.rdb` to S3 daily.

### Vault
- **Storage Backend**: Consul or Raft (integrated).
- **Snapshot**: `vault operator raft snapshot save`.
- **Frequency**: Hourly.

## Disaster Recovery
- **RTO (Recovery Time Objective)**: 1 hour.
- **RPO (Recovery Point Objective)**: 15 minutes.
- **Drill**: Quarterly restoration test.
