# Security Policy

This document outlines the security measures implemented in the X-Tern Agents Disruption Response Planner.

## Authentication

### JWT Authentication
- **Token-based authentication** using JSON Web Tokens (JWT)
- **Password hashing** with bcrypt (industry-standard password hashing)
- **Token expiration**: Configurable via `JWT_EXPIRATION_MINUTES` (default: 1440 minutes / 24 hours)
- **Token refresh**: Not implemented; users must re-authenticate after expiration

### Roles and Permissions
Two built-in roles with different access levels:

| Role | Capabilities |
|------|-------------|
| `warehouse_manager` | Full access: view, create, approve/reject scenarios, view audit logs |
| `analyst` | Limited access: view disruptions, run planner, view scenarios (cannot approve/reject) |

### No OAuth/SSO
- Currently uses local username/password authentication only
- OAuth/SSO integration not implemented in current version

## Transport Security

### HTTPS (Production)
- **HTTPS required** for production deployments
- TLS certificates should be configured at the load balancer or reverse proxy level
- Recommended: Use Let's Encrypt or AWS ACM for certificates

### HTTP (Local Development)
- HTTP allowed for local development (`localhost`, `127.0.0.1`)
- Set `APP_ENV=development` to enable development mode

## Secrets Management

### Environment Variables Only
All secrets are loaded from environment variables. **Never commit secrets to version control.**

Required secrets:
- `JWT_SECRET`: JWT signing key (minimum 32 characters in production)
- `DATABASE_URL`: Database connection string with credentials

Optional secrets:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: For AWS services (if not using IAM roles)

### .env Files
- Use `.env` files for local development
- `.env.example` provided as a template (contains no real secrets)
- `.env` files are gitignored to prevent accidental commits

### No Committed Secrets
The following checks are recommended:
- Use `git-secrets` or similar tools to prevent secret commits
- Scan commits with tools like `trufflehog` or `gitleaks`

## Database Security

### Connection Security
- Use encrypted connections (SSL/TLS) for PostgreSQL in production
- SQLite used only for local development

### Least Privilege
- Application database user should only have necessary permissions:
  - `SELECT`, `INSERT`, `UPDATE`, `DELETE` on application tables
  - No `DROP`, `CREATE TABLE`, or administrative access

### Encryption at Rest
- Handled by database provider:
  - AWS RDS: Enable encryption at creation
  - SQLite: Local development only, no encryption

### SQL Injection Prevention
- All database queries use SQLAlchemy ORM or parameterized queries
- No raw SQL string concatenation with user input

## Logging and Audit

### Audit Logs
- All agent decisions are logged to `decision_logs` table
- Logs include:
  - Pipeline run ID
  - Agent name
  - Input/output summaries
  - Confidence scores
  - Human decisions (approve/reject)
  - Approver information

### What We Log
- ✅ Decision metadata (agent name, step, confidence)
- ✅ Approval/rejection with approver ID
- ✅ Pipeline execution flow
- ✅ Error messages (sanitized)

### What We Don't Log
- ❌ Password or credentials
- ❌ Full JWT tokens
- ❌ Personally Identifiable Information (PII)
- ❌ Raw customer order details beyond IDs

### Log Retention
- Audit logs are retained indefinitely by default
- Implement log rotation and archival as needed for compliance

## API Security

### Input Validation
- All API inputs validated with Pydantic schemas
- Request size limits enforced

### Rate Limiting
- Not implemented in current version
- Recommended for production: Use reverse proxy (nginx) or API gateway

### CORS
- CORS origins restricted to known frontend URLs
- Configurable via `CORS_ORIGINS` setting

## Vulnerability Reporting

If you discover a security vulnerability, please:

1. **Do not** create a public GitHub issue
2. Email the maintainers directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
3. Allow reasonable time for a fix before public disclosure

## Security Checklist for Production

Before deploying to production, ensure:

- [ ] `JWT_SECRET` is a strong, unique, random string (32+ characters)
- [ ] `APP_ENV=production` is set
- [ ] HTTPS is configured with valid TLS certificates
- [ ] Database uses encrypted connections
- [ ] Database user has least-privilege access
- [ ] `.env` files are not in version control
- [ ] Rate limiting is configured at reverse proxy
- [ ] Audit logging is enabled and monitored
- [ ] Regular security updates are applied to dependencies

## Dependencies

Keep dependencies updated to patch security vulnerabilities:

```bash
# Check for known vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade -r requirements.txt
```

## Compliance Notes

This system is designed to support:
- **Audit trails** for decision accountability
- **Human-in-the-loop** approval workflows
- **Role-based access control** for separation of duties

For specific compliance requirements (SOX, HIPAA, etc.), additional measures may be needed.
