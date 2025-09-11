# Supported targets: el9, el10

%if 0%{?rhel} >= 10
%undefine gomodulesmode
%global source_date_epoch_from_changelog 0
%endif

%define gobuild_vendor() %{lua:
    local gobuild = rpm.expand('%{gobuild}')
    gobuild = gobuild:gsub('go build', 'go build -mod=vendor', 1)
    print(gobuild)
}

Name: owasp-coraza-spoa
Version: 0.4.0
Release: 1%{?dist}.zenetys
Summary: OWASP Coraza SPOA for HAProxy SPOE
License: Apache-2.0
URL: https://github.com/corazawaf/coraza-spoa

Source0: https://github.com/corazawaf/coraza-spoa/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1: coraza-spoa.logrotate
Source2: coraza-engine.conf
Source3: coraza-spoa.yaml

Patch0: coraza-spoa-service.patch

BuildRequires: go-rpm-macros
BuildRequires: golang >= 1.23
BuildRequires: systemd-rpm-macros

# caching of go module dependencies
BuildRequires: tar
BuildRequires: xz

%{?systemd_requires}

%description
Coraza SPOA is a system daemon which brings the Coraza WAF as a backing service
for HAProxy. It is written in Go, Coraza supports ModSecurity SecLang rulesets
and is 100% compatible with the OWASP Core Rule Set v4.

%prep
%setup -n coraza-spoa-%{version}
%patch -P 0 -p0

%build
export GOPATH=$PWD/gopath

govendor_coraza_spoa=govendor_coraza_spoa_$(md5sum go.mod |awk '{print $1}').tar.xz
if [ -f %_sourcedir/$govendor_coraza_spoa ]; then
    tar xvJf %{_sourcedir}/$govendor_coraza_spoa
else
    go mod vendor
    tar cJf %{_sourcedir}/$govendor_coraza_spoa ./vendor/
fi

%gobuild_vendor

%install
install -D -p -m 0755 -t %{buildroot}/%{_sbindir}/ ./coraza-spoa
install -D -p -m 0644 -t %{buildroot}/%{_unitdir}/ ./contrib/coraza-spoa.service
install -D -p -m 0644 %{SOURCE1} %{buildroot}/%{_sysconfdir}/logrotate.d/coraza-spoa
install -D -p -m 0644 %{SOURCE2} %{buildroot}/%{_sysconfdir}/coraza-spoa/coraza-engine.conf
install -D -p -m 0644 %{SOURCE3} %{buildroot}/%{_sysconfdir}/coraza-spoa/coraza-spoa.yaml
install -d -m 0750 %{buildroot}/%{_localstatedir}/log/coraza-spoa

%pre
if ! getent group coraza-spoa >/dev/null; then
    groupadd -r coraza-spoa
fi
if ! getent passwd coraza-spoa >/dev/null; then
    useradd -r -g coraza-spoa -d /var/empty -M -s /sbin/nologin coraza-spoa
fi

%post
%systemd_post coraza-spoa.service

%preun
%systemd_preun coraza-spoa.service

%postun
%systemd_postun_with_restart coraza-spoa.service

%files
%defattr(-, root, root, -)
%license LICENSE
%doc CHANGELOG.md README.md
%dir %{_sysconfdir}/coraza-spoa
%config(noreplace) %{_sysconfdir}/coraza-spoa/coraza-engine.conf
%config(noreplace) %{_sysconfdir}/coraza-spoa/coraza-spoa.yaml
%config(noreplace) %{_sysconfdir}/logrotate.d/coraza-spoa
%{_sbindir}/coraza-spoa
%{_unitdir}/coraza-spoa.service
%attr(-, coraza-spoa, adm) %dir %{_localstatedir}/log/coraza-spoa
