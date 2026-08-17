<h1 align="center">ParticleOS Stalwart</h1>

<p align="center">
  A minimal, PostgreSQL-only Stalwart package for the ParticleOS mailserver image.
</p>

<p align="center">
  <strong>Stalwart 0.16.17 for Fedora 44 on x86-64.</strong>
</p>

## Table of Contents

- [Purpose](#purpose)
- [Package Layout](#package-layout)
- [Security and Hardening](#security-and-hardening)
- [Runtime Contract](#runtime-contract)
- [Network Surface](#network-surface)
- [Build and Publish](#build-and-publish)
- [Verification](#verification)
- [Known Cryptography Constraint](#known-cryptography-constraint)
- [Licensing](#licensing)

## Purpose

This repository contains the reviewed, non-generated inputs for the
`home:thefutureisprivate/stalwart` OBS package. It builds the AGPL Stalwart
server from source with Fedora's Rust toolchain and publishes the runtime,
fixed identity, host integration, and SELinux policy as separate RPMs.

OBS stores the generated upstream and Cargo vendor archives and is the
authoritative builder, signer, and publisher. Generated archives and RPMs are
not committed to Git.

## Package Layout

| RPM | Contents | Installed location |
| --- | --- | --- |
| `stalwart` | Server executable, hardened allocator dependencies, packaged WebUI | Signed Stalwart service image |
| `stalwart-particleos-user` | Fixed UID/GID 993 | Host and service image |
| `stalwart-particleos-host` | systemd unit, immutable configuration seed, persistent-directory policy | ParticleOS host |
| `stalwart-selinux` | Dedicated SELinux policy module | ParticleOS host |

The current package is Stalwart `0.16.17-22` with WebUI `1.0.8`. Only the
PostgreSQL backend is compiled. Embedded databases, alternative SQL stores,
cloud storage, queue services, distributed coordination, and proprietary
enterprise source are excluded.

## Security and Hardening

- Cargo runs offline and frozen against the complete vendored lockfile.
- `ossify.py` removes Enterprise-licensed Rust source before any build script
  executes, and the build rejects remaining `LicenseRef-SEL` files.
- The unused vulnerable `fast-float` dependency is removed before compilation.
- The server uses libc allocation so ParticleOS `hardened_malloc` can
  interpose; `no_rlimit_as` remains preloaded for the service.
- Release integer-overflow checks are enabled in the patched Cargo profile.
- Rust output is PIE with RELRO, immediate binding, a non-executable stack,
  frame pointers, ThinLTO, and the LLVM linker.
- Listener binding fails closed if any configured address cannot be bound.
- The WebUI release archive is pinned by SHA-256, installed as an immutable
  local file, and cannot be replaced through Stalwart's network update path.
- A dedicated SELinux domain limits configuration, WebUI, state, logs, runtime
  files, PostgreSQL socket access, resolver access, and the selected protocol
  ports.

Every HTTP response passes through a non-overridable browser policy containing
CSP, HSTS on TLS responses, `nosniff`, clickjacking protection, a restrictive
referrer policy, opener/resource isolation, permissions policy, and legacy
cross-domain denial. Login and device-authorization responses use `no-store`.
The CSP permits only the hashes required by the packaged login page and does
not allow `unsafe-eval` or general inline scripts.

## Runtime Contract

The ParticleOS host supplies PostgreSQL 18 over
`/run/postgresql/.s.PGSQL.5432`. The `stalwart` operating-system account maps
to the same unprivileged PostgreSQL role through peer authentication, so no
database password or environment secret exists.

The host also supplies `systemd-resolved`. Stalwart sends TCP DNS requests only
to resolved's loopback proxy at `127.0.0.54:53`; resolved carries them over the
host's authenticated DNS-over-TLS path while preserving DNSSEC records for
Stalwart's local DANE validation.

The executable and WebUI run from a signed, dm-verity-protected systemd
`RootImage=` service image. The ParticleOS host installs only the fixed
identity, service integration, SELinux policy, PostgreSQL, and image selector.

## Network Surface

| Protocol | Port | Exposure |
| --- | ---: | --- |
| SMTP | TCP 25 | Public |
| HTTPS / WebUI | TCP 443 | Public |
| Implicit-TLS submission | TCP 465 | Public |
| IMAPS | TCP 993 | Public |
| Recovery WebUI | TCP 8080 | Loopback only |

POP3, ManageSieve, plaintext client protocols, and PostgreSQL are not exposed.
Public listeners bind explicitly to IPv4 and IPv6. Stalwart egress is limited
by the ParticleOS host firewall to SMTP TCP 25, HTTPS TCP 443, and the local
resolver proxy.

Fedora labels TCP 993 with the historical `pop_port_t` SELinux type. The
Stalwart domain receives bind permission for that type solely to provide
IMAPS; neither the compiled registry nor the ParticleOS firewall enables POP.

## Build and Publish

The source services use `manual` mode because build.opensuse.org does not
provide the `cargo_vendor` service used by this package. Run source preparation
from the authenticated tools distrobox:

```sh
osc service manualrun
osc diff
osc commit
osc results home:thefutureisprivate stalwart
```

Before committing, review the upstream archive, regenerated vendor archive,
Cargo lockfile, accepted RustSec findings, WebUI digest, patches, and source
service diff. The package builds only in the `stalwart_Fedora_44` x86-64
repository.

## Verification

OBS runs the patched HTTP-policy, local-application, listener, datastore, and
server tests. Release verification also checks:

- the RPM and repository signatures;
- the exact package and WebUI versions;
- absence of jemalloc and Enterprise-licensed source;
- the WebUI archive and generated response digests;
- PIE, RELRO, immediate binding, and non-executable-stack properties;
- the four-package file split and fixed identity;
- SELinux policy installation and the dedicated runtime domain; and
- startup and protocol health from the signed ParticleOS service image.

## Known Cryptography Constraint

The current source graph uses the RustCrypto `rsa` crate affected by
`RUSTSEC-2023-0071`, for which no fixed release is available. ParticleOS
deployments must use Ed25519 DKIM signing keys. The `_service` file records the
accepted advisory together with the disabled-feature or removal rationale for
every other audited finding.

## Licensing

Stalwart, the packaged WebUI, and the downstream source patches are distributed
under [AGPL-3.0-only](LICENSE). Attribution and repository scope are recorded
in [NOTICE](NOTICE). Generated Cargo vendor sources retain their individual
upstream licenses.
