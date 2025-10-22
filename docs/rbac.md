# ASTRA Role-Based Access Control (RBAC)

This document outlines the RBAC system used in ASTRA for user authorization and access control.

## Roles

ASTRA defines the following user roles:

### Admin

Full system access with ability to:

- Manage users and roles
- Access and modify any user's memory
- Install and configure plugins
- View system metrics and analytics
- Configure system settings

### User (Standard)

Normal user access including:

- Read and write own memory
- Use approved plugins
- View own analytics
- Basic system operations

### ReadOnly

Limited access for monitoring:

- Read-only access to own memory
- View own analytics
- No write operations allowed

### Service

Special role for service integrations:

- Read/write memory access
- Analytics reporting
- Tool usage
- No plugin or admin capabilities

## Permission Scopes

### Basic Scopes

- `basic`: Basic system access
- `read`: General read operations
- `write`: General write operations
- `admin`: Administrative operations

### Memory Scopes

- `memory:read`: Read memory entries
- `memory:write`: Create/update memory entries
- `memory:delete`: Delete memory entries
- `memory:admin`: Access any user's memory

### Plugin Scopes

- `plugin:use`: Use installed plugins
- `plugin:install`: Install new plugins
- `plugin:manage`: Configure and manage plugins

### OS Operation Scopes

- `os:read`: Read system files
- `os:write`: Write system files
- `os:execute`: Execute system commands
- `os:network`: Network operations

### Tool Scopes

- `tool:use`: Use available tools
- `tool:manage`: Configure and manage tools

### Analytics Scopes

- `analytics:read`: View analytics data
- `analytics:write`: Record analytics data

## Role-Scope Mapping

### Admin Role

✓ All scopes

### User Role

- `basic`
- `read`
- `write`
- `memory:read`
- `memory:write`
- `plugin:use`
- `os:read`
- `os:write`
- `tool:use`
- `analytics:read`

### ReadOnly Role

- `basic`
- `read`
- `memory:read`
- `analytics:read`

### Service Role

- `basic`
- `read`
- `write`
- `memory:read`
- `memory:write`
- `tool:use`
- `analytics:write`

## Memory Isolation

Each user's memory is completely isolated unless accessed by an admin. The isolation system ensures:

1. Users can only access their own memory
2. Memory operations respect RBAC scopes
3. Quotas are enforced per-user
4. Performance impact < 5%

## Performance Requirements

The RBAC and memory isolation systems must maintain:

- Write operations: p95 latency < 5ms
- Read operations: p95 latency < 1ms
- Quota checks: < 0.1ms overhead
- Total memory overhead: < 5% per user

## Security Considerations

1. JWT tokens must be validated on every request
2. Scope checks occur before any privileged operation
3. Memory isolation is enforced at the data store level
4. Failed access attempts are logged and monitored
5. Admin actions create audit trail entries

## Configuration

The RBAC system is configured through:

1. Environment variables

   - `ASTRA_JWT_SECRET`: JWT signing key
   - `ASTRA_AUTH_ENABLED`: Enable/disable auth (default: true)

2. Memory quotas

   - `max_keys_per_user`: Maximum memory keys per user
   - `max_value_size_bytes`: Maximum size per value
   - `max_total_size_bytes`: Maximum total memory per user