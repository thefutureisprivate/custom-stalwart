%global toolchain clang

Name:           stalwart
Version:        0.16.17
Release:        1%{?dist}
Summary:        Secure mail and collaboration server
License:        AGPL-3.0-only
URL:            https://stalw.art/
Source0:        https://github.com/stalwartlabs/stalwart/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        vendor.tar.zst
Source2:        stalwart.service
Source3:        stalwart.sysusers
Source4:        stalwart.tmpfiles
Source5:        stalwart-config.json
Source6:        stalwart.env
# fast-float is unused by Stalwart but is unsound and can segfault on empty
# input (RUSTSEC-2024-0379 and RUSTSEC-2025-0003). Do not compile it in.
Patch0:         remove-unused-fast-float.patch

BuildRequires:  cargo >= 1.95
BuildRequires:  clang
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  lld
BuildRequires:  perl
BuildRequires:  python3
BuildRequires:  rust >= 1.95
BuildRequires:  systemd-rpm-macros
BuildRequires:  zstd
Requires:       group(stalwart)
Requires:       user(stalwart)
ExclusiveArch:  x86_64

%description
Stalwart is an all-in-one mail and collaboration server supporting SMTP,
IMAP, JMAP, POP3, ManageSieve, CalDAV, CardDAV, and WebDAV. This ParticleOS
build is compiled from source with only the PostgreSQL backend and runs
under a dedicated account with a restrictive systemd sandbox.

%prep
%autosetup -a1 -p1

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
export CARGO_PROFILE_RELEASE_OVERFLOW_CHECKS=true
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

%install
install -Dpm0755 target/release/stalwart \
    %{buildroot}%{_bindir}/stalwart
install -Dpm0644 %{SOURCE2} \
    %{buildroot}%{_unitdir}/stalwart.service
install -Dpm0644 %{SOURCE3} \
    %{buildroot}%{_sysusersdir}/stalwart.conf
install -Dpm0644 %{SOURCE4} \
    %{buildroot}%{_tmpfilesdir}/stalwart.conf
install -Dpm0644 %{SOURCE5} \
    %{buildroot}%{_prefix}/lib/stalwart/config.json
install -Dpm0600 %{SOURCE6} \
    %{buildroot}%{_prefix}/lib/stalwart/stalwart.env

%check
# Exercise the CLI without starting listeners or touching persistent state.
target/release/stalwart --version

%post
%systemd_post stalwart.service

%preun
%systemd_preun stalwart.service

%postun
%systemd_postun_with_restart stalwart.service

%files
%license LICENSES/AGPL-3.0-only.txt
%doc CHANGELOG.md README.md
%{_bindir}/stalwart
%{_unitdir}/stalwart.service
%{_sysusersdir}/stalwart.conf
%{_tmpfilesdir}/stalwart.conf
%dir %{_prefix}/lib/stalwart
%{_prefix}/lib/stalwart/config.json
%{_prefix}/lib/stalwart/stalwart.env

%changelog
* Fri Aug 14 2026 ParticleOS <contact@thefutureisprivate.dev> - 0.16.17-1
- Build the AGPL source in OBS with the upstream dependency lock and no network
- Limit storage support to PostgreSQL and remove the unused vulnerable fast-float crate
- Add a dedicated system account, immutable defaults, and hardened systemd unit
- Use thin LTO and line-table debug data for maintainable automated rebuilds
