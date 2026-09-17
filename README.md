# Ansible Role: pgadmin

![GitHub](https://img.shields.io/github/license/jomrr/ansible-role-pgadmin)
![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-role-pgadmin)
![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-role-pgadmin)
[![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-pgadmin/dev.yml?branch=dev&label=dev)](https://github.com/jomrr/ansible-role-pgadmin/actions/workflows/dev.yml?query=branch%3Adev)
[![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-pgadmin/main.yml?branch=main&label=main)](https://github.com/jomrr/ansible-role-pgadmin/actions/workflows/main.yml?query=branch%3Amain)

Install pgAdmin 4 application packages and manage system-wide settings for web
deployment.

## Purpose

Installs the pgAdmin 4 application for a separately managed web deployment.
System settings live outside the package installation in
/etc/pgadmin/config_system.py, so replacing package-owned files during upgrades
does not overwrite them.

## Scope

### Managed

- Application packages from native repositories or the official pgAdmin APT/Yum
  repository.
- The official repository and its signing key when pgadmin_package_source is
  official.
- System-wide pgAdmin settings, configuration ownership and permissions; server
  mode is always enabled.
- A security baseline for host validation, proxy trust, HTTPS cookies,
  authentication, sessions and optional application features.
- Selection of SQLite or PostgreSQL for pgAdmin's own settings database through
  CONFIG_DATABASE_URI.

### Not Managed

- Webservers, virtual hosts, WSGI services, TLS certificates and service
  restarts.
- Database servers, database/schema/user creation, application database
  initialization, data migration and writable runtime directories.
- Native or third-party distribution repositories and migration between existing
  package providers.

## Requirements

- Native mode requires a repository providing the selected application packages.
  Fedora provides pgadmin4 directly; RPM Fusion is not required for Fedora's
  pgadmin4 package.
- The role matrix covers AlmaLinux, Debian, Fedora and Ubuntu, which have
  official pgAdmin package repositories. openSUSE is outside this matrix because
  the project does not provide repositories for it.
- Official mode requires a distribution release and architecture currently
  published by pgAdmin: Debian/Ubuntu or Fedora/RHEL-compatible systems on
  x86_64. See the linked upstream support tables.
- pgadmin_config_group is required and must name an existing group of the
  separately managed application runtime. With mode '0640', the runtime needs
  this group to read config_system.py; an unrelated root group would prevent
  configuration loading. Fedora's native pgAdmin package creates no pgadmin user
  or group. Direct Fedora HTTPD/mod_wsgi deployments normally use apache; a
  dedicated Gunicorn account and group must be provisioned separately, as in the
  complete proxy example below.
- The default session cookies require HTTPS, and HSTS is enabled for the
  application hostname. Configure HTTPS in the separately managed webserver and
  set pgadmin_config.ALLOWED_HOSTS to the names used in browsers. The default
  allowlist contains only localhost and 127.0.0.1; unlisted Host headers are
  rejected.
- PostgreSQL requires an existing database and login with the privileges needed
  to create and migrate pgAdmin's tables. Create any schema selected in the URI
  beforehand. The pgAdmin application environment must include its PostgreSQL
  driver. Both the official application packages and Fedora's native package
  provide it.

## Dependencies

```yaml
collections:
  - name: community.general
    version: '>=12.0.0'
  - name: community.postgresql
    version: '>=3.12.0,<5.0.0'
```

## Role Variables

### `pgadmin_package_source`

Type: `str`. Required: `false`.

Use existing native repositories or configure the official pgAdmin project
repository.
Native repositories, including any third-party distribution repositories, must
be configured separately.

Default:

```yaml
pgadmin_package_source: native
```

### `pgadmin_config_database_uri`

Type: `str`. Required: `false`.

Connection URI for the pgAdmin settings database; an empty string selects the
default SQLite backend.
PostgreSQL accepts postgresql:// or postgresql+psycopg:// URIs, including
schema, TLS and passfile query parameters.
Overrides CONFIG_DATABASE_URI in pgadmin_config. Keep pgadmin_no_log enabled
when the URI contains credentials.
SQLite and PostgreSQL are the backends currently documented by pgAdmin; other
SQLAlchemy dialects are not promised as supported.

Default:

```yaml
pgadmin_config_database_uri: ''
```

### `pgadmin_config_defaults`

Type: `dict`. Required: `false`.

Security baseline merged with pgadmin_config; override individual settings
through pgadmin_config.
Defaults require HTTPS and permit only localhost and 127.0.0.1 host headers,
with X-Forwarded-* trust disabled.
Replacing this entire mapping replaces the baseline; ordinary site configuration
should use pgadmin_config.

Default:

```yaml
pgadmin_config_defaults:
  ALLOWED_HOSTS:
    - localhost
    - 127.0.0.1
  PROXY_X_FOR_COUNT: 0
  PROXY_X_PROTO_COUNT: 0
  PROXY_X_HOST_COUNT: 0
  PROXY_X_PORT_COUNT: 0
  PROXY_X_PREFIX_COUNT: 0
  SESSION_COOKIE_SECURE: true
  SESSION_COOKIE_HTTPONLY: true
  SESSION_COOKIE_SAMESITE: Lax
  SESSION_COOKIE_DOMAIN: null
  COOKIE_DEFAULT_DOMAIN: null
  COOKIE_DEFAULT_PATH: /
  ENHANCED_COOKIE_PROTECTION: true
  STRICT_TRANSPORT_SECURITY_ENABLED: true
  STRICT_TRANSPORT_SECURITY: max-age=31536000
  X_FRAME_OPTIONS: SAMEORIGIN
  X_CONTENT_TYPE_OPTIONS: nosniff
  X_XSS_PROTECTION: '0'
  CROSS_ORIGIN_OPENER_POLICY: same-origin
  AUTHENTICATION_SOURCES:
    - internal
  SECURITY_PASSWORD_HASH: pbkdf2_sha512
  PASSWORD_LENGTH_MIN: 14
  MAX_LOGIN_ATTEMPTS: 3
  SESSION_EXPIRATION_TIME: 1
  USER_INACTIVITY_TIMEOUT: 3600
  OVERRIDE_USER_INACTIVITY_TIMEOUT: true
  MFA_ENABLED: true
  MFA_SUPPORTED_METHODS:
    - authenticator
  MFA_FORCE_REGISTRATION: false
  ALLOW_SAVE_PASSWORD: false
  SUPPORT_SSH_TUNNEL: false
  ALLOW_SAVE_TUNNEL_PASSWORD: false
  ENABLE_PSQL: false
  ENABLE_BINARY_PATH_BROWSING: false
  ENABLE_SERVER_PASS_EXEC_CMD: false
  SHARED_STORAGE: []
  AUTO_DISCOVER_SERVERS: false
  SHOW_GRAVATAR_IMAGE: false
  UPGRADE_CHECK_ENABLED: false
  LLM_ENABLED: false
  DEBUG: false
  CONSOLE_LOG_LEVEL: 30
  FILE_LOG_LEVEL: 30
  LOG_ROTATION_SIZE: 10
  LOG_ROTATION_AGE: 1440
  LOG_ROTATION_MAX_LOG_FILES: 30
```

### `pgadmin_config`

Type: `dict`. Required: `false`.

Site-specific pgAdmin settings merged over pgadmin_config_defaults and written
to /etc/pgadmin/config_system.py.
Matching keys replace complete values, including lists and nested dictionaries;
unmentioned security defaults remain active.
Use YAML strings, booleans, numbers, null, lists and dictionaries; strings are
literal values, not Python expressions.
SERVER_MODE is always true and CONFIG_DATABASE_URI comes from
pgadmin_config_database_uri, overriding entries in this dictionary.

Default:

```yaml
pgadmin_config: {}
```

### `pgadmin_config_group`

Type: `str`. Required: `true`.

Existing group of the separately managed application runtime, used to make the
system configuration readable by that runtime.
Required because the role does not select a webserver or create runtime
accounts; there is no generally valid default group.

### `pgadmin_config_mode`

Type: `str`. Required: `false`.

Permissions for the system configuration file; root and the configured
application runtime group can read it by default.

Default:

```yaml
pgadmin_config_mode: '0640'
```

### `pgadmin_no_log`

Type: `bool`. Required: `false`.

Suppress configuration task output and diffs by default. Disable only when all
settings and the database URI contain no secrets.

Default:

```yaml
pgadmin_no_log: true
```

## Managed Files

- `/etc/pgadmin/config_system.py` Loaded after config.py, config_distro.py and
  config_local.py; owned by this role in its entirety.
- `/etc/apt/sources.list.d/pgadmin4.sources` Official APT mode only.
- `/etc/apt/keyrings/pgadmin4.asc` Official APT signing key.
- `/etc/yum.repos.d/pgadmin4.repo` Official Yum mode only; package and
  repository signatures are verified.

## Check Mode

Reports pending changes using the modules' check mode support.

- On a fresh host, check mode cannot install repository prerequisites or make
  new repositories available for package resolution.

## Service Behavior

No services are managed. Apply configuration changes by restarting the
separately managed pgAdmin application runtime.

## Operational Notes

- The official pgadmin4-server package contains the web application and its
  Python environment. pgadmin4-web additionally depends on Apache, and the
  pgadmin4 meta-package also installs the desktop runtime. Native Fedora's
  pgadmin4 package contains the application; pgadmin4-httpd provides separate
  Apache integration.
- The role does not run setup-web.sh because it configures Apache. Database
  initialization, writable data/log/session/storage directories and any required
  migrations belong to the separately managed application deployment.
- Package-owned config.py, config_distro.py and config_local.py remain
  untouched. The role merges pgadmin_config_defaults with pgadmin_config and
  replaces its complete config_system.py. Site keys replace complete values,
  including lists and dictionaries; unrelated security defaults remain
  effective. Removing a site key restores the baseline value, or the earlier
  package configuration when the baseline has no such key. SERVER_MODE remains
  true and CONFIG_DATABASE_URI is controlled by pgadmin_config_database_uri.
- An empty pgadmin_config_database_uri uses SQLite. Its file location can be set
  through pgadmin_config.SQLITE_PATH; otherwise pgAdmin derives the location
  from its data directory and package defaults. A PostgreSQL URI selects an
  external settings database. Switching backends changes the connection
  configuration; it does not copy existing users, preferences or saved servers
  between databases.
- The upstream documentation currently describes SQLite and PostgreSQL as
  settings backends. A generic SQLAlchemy URI format does not establish support
  for other database engines. PostgreSQL URIs may specify a schema, SSL options
  or a passfile; percent-encode reserved characters in URI credentials.
- The RPM repository URL retains literal $releasever and $basearch variables.
  DNF resolves them for the target release during a distribution upgrade instead
  of retaining the old Fedora release number. The target release must also be
  published by pgAdmin; the role does not perform the operating-system upgrade.
- Settings are Python literals, so booleans, null and nested structures retain
  their YAML types. Use numeric logging levels such as 30 instead of Python
  expressions such as logging.WARNING. Python compilation validates syntax
  before installation, but does not validate pgAdmin option names or application
  semantics.
- Configuration task output and diffs are hidden by default, and the
  configuration file uses mode '0640'. Disable pgadmin_no_log only for entirely
  non-secret settings. Store credentials in Ansible Vault or another secret
  source.
- All five PROXY_X_*_COUNT settings default to 0. For a reverse proxy,
  explicitly trust the number of proxies setting each header; the proxy must
  overwrite untrusted forwarded headers. Direct WSGI deployments need no
  forwarded-header trust. ENHANCED_COOKIE_PROTECTION binds sessions to client
  addresses; changing addresses behind a proxy may invalidate sessions.
- pgAdmin's WSGI wrapper also honors X-Script-Name and X-Scheme independently of
  the PROXY_X_*_COUNT settings. The separately managed webserver must strip
  these incoming headers or supply trusted values itself. The role cannot
  disable this upstream behavior through the documented configuration settings.
- Cookies use Secure, HttpOnly, SameSite=Lax and no explicit domain. HSTS uses
  max-age=31536000 without includeSubDomains, leaving transport policy for other
  subdomains under separate control. Frame embedding is limited to the same
  origin. X-XSS-Protection is '0' because the legacy browser filter is
  deprecated and can introduce vulnerabilities; see the MDN reference. The
  package's Content-Security-Policy remains in effect; this role does not invent
  a policy for version-specific frontend assets.
- Internal authentication uses pbkdf2_sha512, a 14-character password minimum
  and three failed attempts before account locking. Sessions expire after one
  day and idle users are logged out after 3600 seconds.
  OVERRIDE_USER_INACTIVITY_TIMEOUT=true pauses the idle timeout while
  long-running queries or debugger operations are active.
- TOTP MFA is enabled. Enrollment is not forced by default; users without
  enrollment have no second factor. Set pgadmin_config.MFA_FORCE_REGISTRATION to
  true when users are ready. Existing email-only MFA users need re-enrollment or
  an explicit MFA_SUPPORTED_METHODS override retaining email and the
  corresponding mail configuration.
- Password saving, SSH tunnels, PSQL, binary-path browsing and server password
  commands are disabled. Shared storage, server autodiscovery, Gravatar,
  application upgrade checks and LLM features are disabled. These settings do
  not erase previously stored credentials or rotate existing account passwords.
  Debug mode is disabled; console and file logging use WARNING (30), with 10
  MiB/daily rotation and 30 retained files.
- Language selection and the settings database backend remain deployment
  choices. LANGUAGES can be set through pgadmin_config; SQLite remains the
  default backend. A PostgreSQL Unix-socket URI requires a separately configured
  database and peer/pg_ident mapping matching the operating-system identity of
  the application runtime.
- Changing package source does not remove old repositories or packages. Prepare
  provider migrations separately to avoid package conflicts.

## Supported Platforms

| OS Family | Distribution | Version | Container Image |
| --------- | ------------ | ------- | --------------- |
| RedHat | AlmaLinux | latest | [jomrr/molecule-almalinux:latest](https://hub.docker.com/r/jomrr/molecule-almalinux) |
| Debian | Debian | latest | [jomrr/molecule-debian:latest](https://hub.docker.com/r/jomrr/molecule-debian) |
| RedHat | Fedora | latest | [jomrr/molecule-fedora:latest](https://hub.docker.com/r/jomrr/molecule-fedora) |
| Debian | Ubuntu | latest | [jomrr/molecule-ubuntu:latest](https://hub.docker.com/r/jomrr/molecule-ubuntu) |

## Example Playbook

### Native Fedora packages with SQLite

This example assumes an existing Fedora HTTPD/mod_wsgi runtime using the
`apache` group. Its writable application directories are managed separately.

```yaml
---
- name: Configure pgAdmin application packages
  hosts: all
  gather_facts: true
  roles:
    - role: jomrr.pgadmin
      pgadmin_package_source: native
      pgadmin_config_group: apache
      pgadmin_config:
        ALLOWED_HOSTS:
          - pgadmin.example.org
        LOGIN_BANNER: 'Database administration'
        SQLITE_PATH: /srv/pgadmin/settings.db
```

### Official packages with PostgreSQL settings storage

```yaml
---
- name: Configure pgAdmin from the project repository
  hosts: all
  gather_facts: true
  roles:
    - role: jomrr.pgadmin
      pgadmin_package_source: official
      pgadmin_config_group: pgadmin
      pgadmin_config_database_uri: >-
        postgresql://pgadmin@db.example.org:5432/pgadmin?passfile=/etc/pgadmin/pgpass&sslmode=verify-full
      pgadmin_config:
        ALLOWED_HOSTS:
          - pgadmin.example.org
        DEFAULT_BINARY_PATHS:
          pg: /usr/bin
        DATA_DIR: /srv/pgadmin
```

### Local PostgreSQL socket with peer authentication

```yaml
---
- name: Configure pgAdmin behind a separately managed HTTPS runtime
  hosts: all
  gather_facts: true
  roles:
    - role: jomrr.pgadmin
      pgadmin_package_source: official
      pgadmin_config_group: pgadmin
      pgadmin_config_database_uri: 'postgresql://pgadmin@/pgadmin?host=/var/run/postgresql'
      pgadmin_config:
        ALLOWED_HOSTS:
          - pgadmin.example.org
        LANGUAGES:
          en: English
        MFA_FORCE_REGISTRATION: true
```

### PostgreSQL URI with Vault-managed credentials

```yaml
---
- name: Configure the pgAdmin settings database
  hosts: all
  gather_facts: true
  roles:
    - role: jomrr.pgadmin
      pgadmin_package_source: official
      pgadmin_config_database_uri: "{{ vault_pgadmin_database_uri }}"
      pgadmin_config_group: pgadmin
      pgadmin_config:
        ALLOWED_HOSTS:
          - pgadmin.example.org
```

### HTTPD GSSAPI reverse proxy with a private Gunicorn socket

This complete example targets native Fedora packages and serves pgAdmin at
`https://pgadmin.example.org/`. HTTPD terminates TLS and authenticates Kerberos;
Gunicorn runs pgAdmin under a separate account over a Unix socket. The commands,
service and virtual hosts below belong to the surrounding deployment and are
**not installed or managed by this role**.

Replace the hostname, realm and allowed principal throughout. Provision the
service principal `HTTP/pgadmin.example.org@EXAMPLE.ORG` and its current keys in
`/etc/httpd/pgadmin.keytab` through the realm administrator. Configure the host's
`/etc/krb5.conf` for that realm. Install a matching TLS certificate chain at
`/etc/pki/tls/certs/pgadmin.crt` and its private key at
`/etc/pki/tls/private/pgadmin.key`. Clients must trust that issuing CA and have
Kerberos tickets; browser policy must permit SPNEGO for this hostname.

**1. Prepare the external runtime on a dedicated Fedora host.** Run as root:

```bash
dnf install -y httpd mod_ssl mod_auth_gssapi krb5-workstation \
  python3-gunicorn util-linux
useradd --system --user-group --home-dir /var/lib/pgadmin \
  --shell /sbin/nologin pgadmin
usermod --append --groups pgadmin apache
install -d -o pgadmin -g pgadmin -m 0700 /var/lib/pgadmin
chown root:apache /etc/httpd/pgadmin.keytab
chmod 0640 /etc/httpd/pgadmin.keytab
chown root:root /etc/pki/tls/private/pgadmin.key
chmod 0600 /etc/pki/tls/private/pgadmin.key
```

Only the application and HTTPD accounts should belong to the `pgadmin` group;
group membership grants access to the trusted authentication socket. The
private keytab remains readable by HTTPD, without giving the application access.

**2. Apply the role with matching webserver authentication and proxy trust.**

```yaml
---
- name: Configure pgAdmin for the HTTPD Kerberos proxy
  hosts: all
  gather_facts: true
  roles:
    - role: jomrr.pgadmin
      pgadmin_package_source: native
      pgadmin_config_group: pgadmin
      pgadmin_config:
        ALLOWED_HOSTS:
          - pgadmin.example.org
        DATA_DIR: /var/lib/pgadmin
        LOG_FILE: /var/lib/pgadmin/pgadmin4.log
        AUTHENTICATION_SOURCES:
          - webserver
        WEBSERVER_REMOTE_USER: HTTP_X_FORWARDED_USER
        WEBSERVER_AUTO_CREATE_USER: true
        PROXY_X_FOR_COUNT: 1
        PROXY_X_PROTO_COUNT: 1
```

The other three proxy counters retain their zero defaults. HTTPD preserves
the original Host header and supplies exactly one trusted client address and
scheme. Secure cookies, host validation and the remaining security defaults stay
enabled. Authorized principals are automatically created as ordinary pgAdmin
users. `Require user` below limits who can enter; replace its list with the
explicitly permitted full principals. This uses pgAdmin's `webserver` source,
not its separate `kerberos` source, and does not delegate database credentials.

**3. Initialize the application and install the external WSGI service.**

For a fresh settings database, run this interactive command as root before
starting Gunicorn. Supply the bootstrap administrator email and a strong password
when prompted; there is no internal-login fallback in the configuration above.
Manage external administrator accounts separately with pgAdmin's user-management
CLI. Existing databases require their normal backup and migration procedure.

```bash
runuser -u pgadmin -- /usr/bin/python3 /usr/lib/pgadmin4/setup.py setup-db
```

Install `/etc/systemd/system/pgadmin.service`:

```ini
[Unit]
Description=pgAdmin WSGI application
After=network.target

[Service]
User=pgadmin
Group=pgadmin
WorkingDirectory=/usr/lib/pgadmin4
RuntimeDirectory=pgadmin
RuntimeDirectoryMode=0750
StateDirectory=pgadmin
StateDirectoryMode=0700
UMask=0007
ExecStart=/usr/bin/gunicorn --workers=1 --threads=25 --timeout=120 \
    --umask=007 --bind=unix:/run/pgadmin/pgadmin.sock pgAdmin4:app
Restart=on-failure
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

One worker with threads follows pgAdmin's Gunicorn deployment model. The
explicit Gunicorn umask keeps the socket at `0770`; the enclosing directory
is `0750`. There is no TCP backend listener. These Python and application paths
are for Fedora's native package, not the official package's bundled environment.

**4. Configure the separately managed HTTPD.** On this dedicated Fedora host,
replace `/etc/httpd/conf.d/ssl.conf` with the following configuration. Fedora's
main configuration already listens on port 80; declare the HTTPS listener only
once. The packages must load `ssl`, `headers`, `proxy`, `proxy_http`, `alias`,
`auth_gssapi`, `authz_core` and `authz_user`; check with `httpd -M`.

```apache
# Dedicated Fedora HTTPD; the main configuration already listens on port 80.
Listen 443 https
SSLSessionCache shmcb:/run/httpd/sslcache(512000)

<VirtualHost *:80>
    ServerName pgadmin.example.org
    Redirect permanent / https://pgadmin.example.org/
</VirtualHost>

<VirtualHost *:443>
    ServerName pgadmin.example.org
    SSLEngine on
    SSLProtocol -all +TLSv1.2 +TLSv1.3
    SSLCertificateFile /etc/pki/tls/certs/pgadmin.crt
    SSLCertificateKeyFile /etc/pki/tls/private/pgadmin.key

    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders Off

    # Set trusted identity and proxy metadata after authentication (no early).
    RequestHeader unset X-Forwarded-User
    RequestHeader unset X_Forwarded_User
    RequestHeader unset Remote-User
    RequestHeader unset REMOTE_USER
    RequestHeader unset Forwarded
    RequestHeader unset X-Forwarded-Host
    RequestHeader unset X-Forwarded-Port
    RequestHeader unset X-Forwarded-Prefix
    RequestHeader unset X-Forwarded-Protocol
    RequestHeader unset X-Forwarded-Ssl
    RequestHeader unset X-Scheme
    RequestHeader unset X-Script-Name
    RequestHeader unset SCRIPT_NAME
    RequestHeader unset PATH_INFO
    RequestHeader set X-Forwarded-For "expr=%{CONN_REMOTE_ADDR}"
    RequestHeader set X-Forwarded-Proto "https"

    <Location "/">
        AuthType GSSAPI
        AuthName "pgAdmin Kerberos"
        AuthzSendForbiddenOnFailure On
        GssapiCredStore keytab:/etc/httpd/pgadmin.keytab
        GssapiAcceptorName HTTP@pgadmin.example.org
        GssapiAllowedMech krb5
        GssapiSSLonly On
        GssapiLocalName Off
        GssapiBasicAuth Off
        Require user alice@EXAMPLE.ORG

        RequestHeader set X-Forwarded-User "expr=%{REMOTE_USER}"
        RequestHeader unset Authorization
    </Location>

    ProxyPass / unix:/run/pgadmin/pgadmin.sock|http://localhost/ timeout=120
    ProxyPassReverse / http://localhost/
    ErrorLog logs/pgadmin_error.log
    CustomLog logs/pgadmin_access.log combined
</VirtualHost>
```

The identity header uses Apache's authenticated `REMOTE_USER` in the normal
late request phase. Do not add `early` or copy a client-supplied identity.
`Authorization` is removed only after GSSAPI has consumed it. Sanitization also
covers pgAdmin's legacy scheme/path headers and Gunicorn's WSGI forwarding
headers. `GssapiLocalName Off` preserves the realm in usernames. HTTPD requires
a ticket on every request, including requests carrying an existing pgAdmin
session cookie; application logout does not destroy the browser's Kerberos tickets.

Validate and activate the external services after installing all files:

```bash
httpd -t
systemd-analyze verify /etc/systemd/system/pgadmin.service
systemctl daemon-reload
systemctl enable --now pgadmin
systemctl enable httpd
systemctl restart httpd
```

The HTTPD restart applies its supplementary group membership. On SELinux hosts,
the external runtime deployment must also provide suitable labels and policy
for HTTPD's keytab access and connection to the application's Unix socket.
The container validation below does not validate an enforcing SELinux policy.

**5. Check from a Kerberos client that trusts the TLS certificate.**

```bash
kinit alice@EXAMPLE.ORG
curl --negotiate -u : --fail --location \
  --cookie-jar /tmp/pgadmin-cookies --cookie /tmp/pgadmin-cookies \
  https://pgadmin.example.org/browser/js/utils.js
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  -H 'X-Forwarded-User: alice@EXAMPLE.ORG' https://pgadmin.example.org/
```

The first response contains the authenticated full username. The second must
return `401`, because it deliberately sends no Negotiate credentials.

Validated on 2026-09-15 in an isolated Fedora 44 container with pgAdmin 9.17,
HTTPD 2.4.68, mod_auth_gssapi 1.6.5, MIT Kerberos 1.22.2 and Gunicorn 23.0.0.
An actual test KDC issued tickets for allowed and denied principals. Checks
passed for HTTPD/service syntax, SSO identity, forged and duplicate headers,
host rejection, anonymous/session-cookie-only requests, unauthorized principals,
secure cookies, HSTS, CSRF rejection and successful preference write/read.
An unrelated local account could not connect to the Unix socket. Realm-specific
AD/IPA integration and interactive browser policy still require deployment testing.

## References

- [pgAdmin deployment](https://www.pgadmin.org/docs/pgadmin4/latest/deployment.html)
- [Configuration precedence](https://www.pgadmin.org/docs/pgadmin4/latest/config_py.html)
- [Two-factor authentication](https://www.pgadmin.org/docs/pgadmin4/latest/mfa.html)
- [PSQL tool security implications](https://www.pgadmin.org/docs/pgadmin4/latest/psql_tool.html)
- [Legacy XSS filter limitations](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-XSS-Protection)
- [WSGI entry point and legacy proxy headers](https://github.com/pgadmin-org/pgadmin4/blob/master/web/pgAdmin4.py)
- [Server deployment](https://www.pgadmin.org/docs/pgadmin4/latest/server_deployment.html)
- [Webserver authentication](https://www.pgadmin.org/docs/pgadmin4/latest/webserver.html)
- [mod_auth_gssapi configuration](https://github.com/gssapi/mod_auth_gssapi)
- [Apache RequestHeader processing](https://httpd.apache.org/docs/2.4/mod/mod_headers.html#requestheader)
- [Apache reverse proxy and Unix sockets](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html#proxypass)
- [Gunicorn settings and trusted forwarding headers](https://gunicorn.org/reference/settings/)
- [Configuration database backends](https://www.pgadmin.org/docs/pgadmin4/latest/external_database.html)
- [Official APT repository](https://www.pgadmin.org/download/pgadmin-4-apt/)
- [Official RPM repository](https://www.pgadmin.org/download/pgadmin-4-rpm/)
- [Fedora package](https://packages.fedoraproject.org/pkgs/pgadmin4/pgadmin4/)
- [Upstream Debian packaging](https://github.com/pgadmin-org/pgadmin4/blob/master/pkg/debian/build.sh)
- [Upstream RPM packaging](https://github.com/pgadmin-org/pgadmin4/blob/master/pkg/redhat/build.sh)

## Author

[Jonas Mauer](https://github.com/jomrr)

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
