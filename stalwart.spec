%global toolchain clang
%global webui_version 1.0.8
%global webui_sha256 a3904b571aacca815eee2c38dd86de510d53304babe50b9576760bf70a36c0bf

Name:           stalwart
Version:        0.16.17
Release:        9%{?dist}
Summary:        Secure mail and collaboration server
License:        AGPL-3.0-only
URL:            https://stalw.art/
Source0:        https://github.com/stalwartlabs/stalwart/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        vendor.tar.zst
Source2:        stalwart.service
Source3:        stalwart.sysusers
Source4:        stalwart.tmpfiles
Source5:        stalwart-config.json
Source6:        https://github.com/stalwartlabs/webui/releases/download/v%{webui_version}/webui.zip#/%{name}-webui-%{webui_version}.zip
Source7:        https://raw.githubusercontent.com/stalwartlabs/webui/v%{webui_version}/LICENSES/AGPL-3.0-only.txt#/%{name}-webui-AGPL-3.0-only.txt
Source8:        particleos_stalwart.te
Source9:        particleos_stalwart.fc
# fast-float is unused by Stalwart but is unsound and can segfault on empty
# input (RUSTSEC-2024-0379 and RUSTSEC-2025-0003). Do not compile it in.
Patch0:         remove-unused-fast-float.patch
# Replace upstream's built-in jemalloc, enable release overflow checks, and
# enforce the ParticleOS HTTP response security policy in the server itself.
Patch1:         particleos-hardening.patch
# Keep application assets inside the signed OS payload and ship only the
# protocol listeners selected by the ParticleOS mail appliance.
Patch2:         particleos-platform-policy.patch

BuildRequires:  binutils
BuildRequires:  cargo >= 1.95
BuildRequires:  clang
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  lld
BuildRequires:  perl
BuildRequires:  python3
BuildRequires:  rust >= 1.95
BuildRequires:  selinux-policy-devel
BuildRequires:  unzip
BuildRequires:  zstd
Requires:       group(stalwart)
Requires:       hardened_malloc
Requires:       no_rlimit_as
Requires:       systemd-resolved
Requires:       user(stalwart)
ExclusiveArch:  x86_64

%description
Stalwart is a mail and collaboration server supporting SMTP, IMAP, JMAP,
CalDAV, CardDAV, and WebDAV. This ParticleOS build is compiled from source
with only the PostgreSQL backend, serves an OS-managed WebUI bundle, and runs
under a dedicated account with a restrictive systemd sandbox.

%prep
%autosetup -a1 -p1

printf '%s  %s\n' '%{webui_sha256}' '%{SOURCE6}' | sha256sum --check --strict

# The upstream repository contains source under both AGPL-3.0-only and the
# proprietary Stalwart Enterprise License. Remove all proprietary files and
# snippets before any Rust build script is executed.
python3 resources/scripts/ossify.py crates
if grep -R -l -m1 'SPDX-License-Identifier: LicenseRef-SEL' crates --include='*.rs'; then
    echo 'Stalwart Enterprise licensed Rust source remains after ossify' >&2
    exit 1
fi

%build
export CARGO_NET_OFFLINE=true
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1
export CARGO_PROFILE_RELEASE_DEBUG=1
export CARGO_PROFILE_RELEASE_INCREMENTAL=false
export CARGO_PROFILE_RELEASE_LTO=thin
export CARGO_PROFILE_RELEASE_STRIP=none

# Rust executables are PIE on Fedora. Force the hardened LLVM linker path,
# immediate relocation binding, a non-executable stack, and frame pointers.
export RUSTFLAGS="-C linker=clang -C link-arg=-fuse-ld=lld -C link-arg=-Wl,-z,relro,-z,now,-z,noexecstack -C force-frame-pointers=yes"

cargo build \
    --frozen \
    --release \
    -p stalwart \
    --no-default-features \
    --features postgres

install -Dpm0644 %{SOURCE8} selinux/particleos_stalwart.te
install -Dpm0644 %{SOURCE9} selinux/particleos_stalwart.fc
make -C selinux -f /usr/share/selinux/devel/Makefile particleos_stalwart.pp

%install
install -Dpm0755 target/release/stalwart \
    %{buildroot}%{_bindir}/stalwart
install -Dpm0644 %{SOURCE2} \
    %{buildroot}%{_prefix}/lib/systemd/system/stalwart.service
install -Dpm0644 %{SOURCE3} \
    %{buildroot}%{_prefix}/lib/sysusers.d/stalwart.conf
install -Dpm0644 %{SOURCE4} \
    %{buildroot}%{_prefix}/lib/tmpfiles.d/stalwart.conf
install -Dpm0644 %{SOURCE5} \
    %{buildroot}%{_prefix}/lib/stalwart/config.json
install -Dpm0644 %{SOURCE6} \
    %{buildroot}%{_datadir}/stalwart/webui.zip
# Stalwart rewrites this base URL while serving /account. Publish the exact
# expected response digest so the image health gate can detect a stale or
# mismatched runtime bundle without duplicating a version-specific hash.
install -d -m0755 %{buildroot}%{_datadir}/stalwart
unzip -p %{SOURCE6} index.html \
    | sed 's#<base href="/"#<base href="/account/"#' \
    | sha256sum \
    | awk '{print $1}' \
    >%{buildroot}%{_datadir}/stalwart/webui-account.sha256
chmod 0644 %{buildroot}%{_datadir}/stalwart/webui-account.sha256
unzip -p %{SOURCE6} index.html \
    | sed 's#<base href="/"#<base href="/admin/"#' \
    | sha256sum \
    | awk '{print $1}' \
    >%{buildroot}%{_datadir}/stalwart/webui-admin.sha256
chmod 0644 %{buildroot}%{_datadir}/stalwart/webui-admin.sha256
install -Dpm0644 %{SOURCE7} \
    %{buildroot}%{_licensedir}/%{name}/webui-AGPL-3.0-only.txt
install -Dpm0644 selinux/particleos_stalwart.pp \
    %{buildroot}%{_datadir}/selinux/packages/particleos_stalwart.pp

%check
# Keep the policy attached to the final HTTP response boundary and verify the
# exact CSP hashes required by Stalwart's packaged login page.
cargo test --frozen --release -p http@%{version} security_headers::tests
cargo test --frozen --release -p common@%{version} application::tests
cargo test --frozen --release -p common@%{version} defaults::tests
cargo test --frozen --release -p common@%{version} listener::particleos_tests
cargo test --frozen --release -p store@%{version} particleos_tests
cargo test --frozen --release -p stalwart@%{version} particleos_tests \
    --no-default-features --features postgres

# The WebUI is an immutable, checksum-pinned RPM payload rather than a
# first-boot network download. Reject a malformed source archive at build time.
unzip -tq %{SOURCE6}
test -s selinux/particleos_stalwart.pp

# Production Stalwart must use libc allocation so hardened_malloc can interpose.
if strings target/release/stalwart | grep -Eq 'tikv[_-]jemalloc|<jemalloc>'; then
    echo 'The Stalwart binary still contains jemalloc' >&2
    exit 1
fi

# Exercise the CLI without starting listeners or touching persistent state.
# The mailserver image composes this RPM with hardened_malloc from the base
# repository; keeping it out of BuildRequires avoids rebuilding that package in
# Stalwart's independent Fedora_44 repository.
target/release/stalwart --version

%post
if [ -x /usr/lib/systemd/systemd-update-helper ]; then
    /usr/lib/systemd/systemd-update-helper install-system-units \
        stalwart.service || :
fi

%preun
if [ "$1" -eq 0 ] && [ -x /usr/lib/systemd/systemd-update-helper ]; then
    /usr/lib/systemd/systemd-update-helper remove-system-units \
        stalwart.service || :
fi

%postun
if [ "$1" -ge 1 ] && [ -x /usr/lib/systemd/systemd-update-helper ]; then
    /usr/lib/systemd/systemd-update-helper mark-restart-system-units \
        stalwart.service || :
fi

%files
%license LICENSES/AGPL-3.0-only.txt
%license %{_licensedir}/%{name}/webui-AGPL-3.0-only.txt
%doc CHANGELOG.md README.md
%{_bindir}/stalwart
%{_prefix}/lib/systemd/system/stalwart.service
%{_prefix}/lib/sysusers.d/stalwart.conf
%{_prefix}/lib/tmpfiles.d/stalwart.conf
%dir %{_prefix}/lib/stalwart
%{_prefix}/lib/stalwart/config.json
%dir %{_datadir}/stalwart
%{_datadir}/stalwart/webui.zip
%{_datadir}/stalwart/webui-admin.sha256
%{_datadir}/stalwart/webui-account.sha256
%{_datadir}/selinux/packages/particleos_stalwart.pp

%changelog
* Sat Aug 15 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-9
- Remove the volatile systemd-rpm-macros build dependency while preserving its scriptlets

* Sat Aug 15 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-8
- Start fresh installations in loopback-only recovery mode with a temporary admin
- Exit nonzero when database migration or runtime-mode publication fails
- Always load the WebUI from the immutable RPM instead of a mutable blob cache
- Publish the served WebUI digest for protocol-aware image health verification

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-7
- Validate DANE DNSSEC data through systemd-resolved's local TCP proxy stub

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-6
- Abort startup instead of listening on an ephemeral port after a bind failure

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-5
- Permit the Fedora SELinux port type that contains IMAPS TCP 993

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-4
- Bind public listeners explicitly on IPv4 and IPv6
- Keep the bootstrap WebUI listener restricted to IPv4 and IPv6 loopback

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-3
- Package the checksum-pinned WebUI inside the signed immutable OS payload
- Reject runtime WebUI downloads and remove default POP3 and ManageSieve listeners
- Use local PostgreSQL peer authentication without an environment secret
- Ship a dedicated confined SELinux domain and file-context policy

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-2
- Replace the built-in jemalloc allocator with preloaded hardened_malloc
- Enable release-profile integer overflow checks in the patched source
- Enforce CSP, HSTS on TLS, and browser security headers on every HTTP response
- Prevent caching of the embedded login and device authorization page

* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-1
- Build the AGPL source in OBS with the upstream dependency lock and no network
- Limit storage support to PostgreSQL and remove the unused vulnerable fast-float crate
- Add a dedicated system account, immutable defaults, and hardened systemd unit
- Use thin LTO and line-table debug data for maintainable automated rebuilds
