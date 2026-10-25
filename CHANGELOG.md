# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-25

### Fixed

- The seed script no longer prints the demo account passwords (in either the fresh-seed or the already-seeded banner); it points to the README's Demo accounts table instead (CodeQL `py/clear-text-logging-sensitive-data`).
- CodeQL skips test directories, whose throwaway secrets were reported as weak password hashing.

### Added

- API reference and curl-session screenshots in the README.
- CodeQL code scanning workflow (Python, JavaScript/TypeScript and Actions) and Dependabot updates for pip, npm, Docker and GitHub Actions.
- Roadmap tracked as GitHub issues under the v0.2.0 milestone.
- This changelog.

### Changed

- CI workflow runs with a read-only `GITHUB_TOKEN` by default.
- README test counts updated to the current suites (48 backend, 25 frontend).

## [0.1.0] - 2026-10-25

First public release.

### Added

- Auth: bcrypt passwords, 15-minute JWT access tokens and rotating 30-day refresh tokens in httpOnly cookies, reuse detection, email verification, password reset, lockout and per-IP rate limits.
- Tenancy: organizations with owner/admin/member roles, org-scoped queries, last-owner protection and expiring email invites.
- Per-org API keys (`sk_live_…`, hashed at rest) with scopes, expiry and revocation.
- Free / Pro / Business plans with server-side limits (HTTP 402, `plan_limit_reached`) and feature flags.
- Mock billing provider with HMAC-signed webhooks, idempotency, dunning states, and cancel/resume at period end.
- Audit log gated to paid plans and a superuser admin area with platform stats.
- Next.js 14 frontend: marketing site with pricing, auth and onboarding, dashboard with org switcher, team, API keys, billing, settings, audit log and admin.
- Health and readiness endpoints, JSON logs with request ids, Alembic migrations checked in CI, dev and prod compose, nginx and a seed script.
- Live demo kit: Swagger UI on GitHub Pages, Codespaces dev container and Render blueprint.

### Fixed

- Database and backend URLs resolve correctly on managed hosts (deploy-friendly URL handling).

[Unreleased]: https://github.com/AkibUllah/saas-starter-kit/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/AkibUllah/saas-starter-kit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AkibUllah/saas-starter-kit/releases/tag/v0.1.0
