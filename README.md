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
the complete upstream lock. The upstream jemalloc global allocator is removed
so the packaged service uses `hardened_malloc`. Its explicit preload preserves
ParticleOS's `no_rlimit_as` companion library. Rust release-profile integer
overflow checks are enabled in the patched source rather than only through a
build-environment override.

Every response is finalized with a non-overridable browser-security policy:
CSP, TLS-only HSTS, `nosniff`, clickjacking protection, a restrictive referrer
policy, same-origin opener and resource isolation, a restrictive permissions
policy, and legacy cross-domain policy denial. The CSP has no `unsafe-eval` or
general inline-script allowance; its two hashes cover only the packaged login
page's inline script and style. Inline style attributes remain allowed because
the current upstream Web UI generates them. Login and device-authorization
pages are marked `no-store`.

The WebUI is upstream v1.0.8, pinned to the release asset's published
SHA-256 digest and installed in immutable `/usr`. Stalwart accepts only that
exact local bundle path, so registry changes cannot recreate its upstream
first-boot download channel. WebUI changes consequently pass through the same
OBS build, RPM signature, signed image, and system-update verification as the
server binary.

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

The packaged startup configuration connects to the local PostgreSQL Unix
socket as the `stalwart` operating-system account. PostgreSQL peer
authentication maps it to the same unprivileged database role, so no database
password exists in an environment variable or configuration file. The
ParticleOS mailserver image owns database initialization and provisioning.
The package also requires `systemd-resolved`; Stalwart has no independent DNS
egress to external resolvers and uses the local resolved stub exclusively.

The default public protocol set is SMTP 25, implicit-TLS submission 465,
implicit-TLS IMAP 993, and HTTPS 443. POP3 and ManageSieve are not created by
the default registry and are not admitted by the ParticleOS firewall. Public
listeners bind explicitly on both IPv4 and IPv6; the plaintext bootstrap WebUI
listener binds only to `127.0.0.1:8080` and `[::1]:8080`.

Fedora assigns TCP 993 to the historical SELinux `pop_port_t`, which also
contains legacy POP ports. The Stalwart domain therefore needs bind permission
for that Fedora type to provide IMAPS. This does not enable POP: the compiled
registry defaults omit POP listeners, the image health gate rejects unexpected
legacy listeners, and nftables exposes only the four documented public ports.

The RPM also carries a compiled `particleos_stalwart` SELinux policy. The
mailserver image installs it before the final full-filesystem relabel. The
domain may read only its labelled configuration and WebUI, manage its labelled
state/log/runtime trees, connect to PostgreSQL only over its Unix socket,
resolve through the host stub, and bind or connect only to the selected mail
and HTTP port types.

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
