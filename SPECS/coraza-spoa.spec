# Supported targets: el9, el10

%define coraza_spoa_version 0.9.0
%define coreruleset_version 4.25.1

%if 0%{?rhel} >= 10
%undefine gomodulesmode
%global source_date_epoch_from_changelog 0
%endif

%define gobuild_vendor() %{lua:
    local gobuild = rpm.expand('%{gobuild}')
    gobuild = gobuild:gsub('go build', 'go build -mod=vendor', 1)
    print(gobuild)
}

Name: coraza-spoa
Version: %coraza_spoa_version
Release: 1%{?dist}.zenetys
Summary: A wrapper for integrating the OWASP Coraza WAF with HAProxy's SPOE filters
License: Apache-2.0
URL: https://github.com/corazawaf/coraza-spoa

Source0: https://github.com/corazawaf/coraza-spoa/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1: https://github.com/coreruleset/coreruleset/releases/download/v%{coreruleset_version}/coreruleset-%{coreruleset_version}-minimal.tar.gz


Source10: coraza-spoa.logrotate
Source11: coraza-spoa.sysconfig
Source20: config.yaml
Source21: coraza-default-pre-crs.conf
Source22: coraza-default-post-crs.conf

Source30: haproxy.cfg.sample
Source31: haproxy-spoe-coraza.conf.sample

Patch0: coraza-spoa-service.patch
Patch1: coraza-spoa-no-coreruleset.patch

BuildRequires: go-rpm-macros
BuildRequires: golang >= 1.25.7
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
# coraza-spoa
%setup -c
cd coraza-spoa-%{version}
%patch -P 0 -p1
%patch -P 1 -p1
cd ..

# coreruleset
%setup -T -D -a 1

%build
export GOPATH=%{_builddir}/gopath

# coraza-spoa
cd coraza-spoa-%{version}
govendor_coraza_spoa=govendor_coraza_spoa_$(md5sum go.mod |awk '{print $1}').tar.xz
if [ -f %_sourcedir/$govendor_coraza_spoa ]; then
    tar xvJf %{_sourcedir}/$govendor_coraza_spoa
else
    go mod vendor
    tar cJf %{_sourcedir}/$govendor_coraza_spoa ./vendor/
fi
%gobuild_vendor
cd ..

%install
cd coraza-spoa-%{version}
install -D -p -m 0755 -t %{buildroot}/%{_sbindir}/ ./coraza-spoa
install -D -p -m 0644 -t %{buildroot}/%{_unitdir}/ ./contrib/coraza-spoa.service
install -D -p -m 0644 %{SOURCE10} %{buildroot}/%{_sysconfdir}/logrotate.d/coraza-spoa
install -D -p -m 0644 %{SOURCE11} %{buildroot}/%{_sysconfdir}/sysconfig/coraza-spoa
install -D -p -m 0644 -t %{buildroot}/%{_sysconfdir}/coraza-spoa/ %{SOURCE20}
install -D -p -m 0644 %{SOURCE21} %{buildroot}/%{_sysconfdir}/coraza-spoa/default/pre-crs/00-custom.conf
install -D -p -m 0644 %{SOURCE22} %{buildroot}/%{_sysconfdir}/coraza-spoa/default/post-crs/00-custom.conf
install -d -m 0750 %{buildroot}/%{_localstatedir}/log/coraza-spoa
install -D -p -m 0644 -t %{buildroot}/%{_datadir}/coraza-spoa/ vendor/github.com/corazawaf/coraza/v3/coraza.conf-recommended
install -D -p -m 0644 %{SOURCE30} %{buildroot}/%{_datadir}/coraza-spoa/haproxy/haproxy.cfg.sample
install -D -p -m 0644 %{SOURCE31} %{buildroot}/%{_datadir}/coraza-spoa/haproxy/spoe-coraza.conf.sample
cd ..

# coreruleset
install -d -m 0755 %{buildroot}/%{_datadir}/coraza-spoa
cp -a coreruleset-%{coreruleset_version} %{buildroot}/%{_datadir}/coraza-spoa/
ln -s coreruleset-%{coreruleset_version} %{buildroot}/%{_datadir}/coraza-spoa/coreruleset

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
%license coraza-spoa-%{version}/LICENSE
%doc coraza-spoa-%{version}/CHANGELOG.md
%doc coraza-spoa-%{version}/README.md
%dir %{_sysconfdir}/coraza-spoa
%config(noreplace) %{_sysconfdir}/coraza-spoa/config.yaml
%config(noreplace) %{_sysconfdir}/coraza-spoa/default/post-crs/00-custom.conf
%config(noreplace) %{_sysconfdir}/coraza-spoa/default/pre-crs/00-custom.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/coraza-spoa
%config(noreplace) %{_sysconfdir}/sysconfig/coraza-spoa
%{_sbindir}/coraza-spoa
%{_datadir}/coraza-spoa
%{_unitdir}/coraza-spoa.service
%attr(-, coraza-spoa, coraza-spoa) %dir %{_localstatedir}/log/coraza-spoa
