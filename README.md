# Stalwart OBS package

This repository tracks the reviewed, non-generated files mirrored to
`home:thefutureisprivate/stalwart`. OBS is the authoritative source store and
build/signing environment. Generated source and vendor archives deliberately
remain in OBS instead of Git.

The public repository is
[thefutureisprivate/custom-stalwart](https://github.com/thefutureisprivate/custom-stalwart).

The package builds Stalwart from its AGPL source with Rust and Cargo from
Fedora 44. Cargo is forced offline and frozen against the vendored upstream
lock. Only the PostgreSQL backend is enabled; embedded databases, other SQL
databases, cloud-storage, queue, distributed-coordination, and enterprise code
are excluded. Vendor filtering is disabled so `respect-lockfile=true` verifies
the complete upstream lock.

## Approve an update

Source services are in OBS `manual` mode. This is intentional because the
public OBS service workers do not provide `cargo_vendor`; the authenticated
tools distrobox is the source-preparation runner. The scheduled updater checks
for stable upstream releases and currently stops for explicit permission:

1. Review the upstream release and upgrade notes.
2. Change `Version:` and add a changelog entry in `stalwart.spec`.
3. In the OBS package checkout, run `osc service manualrun`.
4. Verify the source archive, regenerated vendor archive, dependency graph,
   and `osc diff`.
5. Commit, wait for the Fedora 44 x86-64 build, then verify the RPM signature,
   hardening flags, file list, and repository publication.

Before enabling the service, create the `stalwart` PostgreSQL database and
role, then set `STALWART_DB_PASSWORD` in `/etc/stalwart/stalwart.env`. The
packaged startup configuration connects to PostgreSQL on `127.0.0.1:5432`,
uses strict certificate validation whenever TLS is enabled, and fails closed
while the required password is absent.

Keep both services in `manual` mode. Once unattended updates are approved,
change the scheduled task from “ask for explicit approval” to “run
`osc service manualrun`, validate, commit, and verify publication.” Removing
that single approval instruction is the whole gate; OBS remains the
builder, signer, and publisher.

## Known upstream cryptography constraint

Stalwart 0.16.17 still uses the RustCrypto `rsa` crate, for which
RUSTSEC-2023-0071 has no fixed release. ParticleOS deployments must use
Ed25519 DKIM signing keys. The package removes the unused vulnerable
`fast-float` crate and excludes optional backends whose dependency closures
contain older vulnerable XML or compression crates. The exact RustSec IDs are
accepted in `_service` with per-finding rationale because the vendoring service
audits the unpatched, all-features lockfile; the RPM build compiles only the
patched PostgreSQL graph.
