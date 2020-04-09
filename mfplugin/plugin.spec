Name: {{NAME}}
Summary: {{SUMMARY}}
Version: {{VERSION}}
Release: 1
License: {{LICENSE}}
Group: Development/Tools
URL: {{URL}}
Buildroot: %{_tmppath}/%{name}-root
Packager: {{PACKAGER | default('unknow') }}
Vendor: {{VENDOR}}
AutoReq: no
AutoProv: no
Prefix: /metwork_plugin

%description
{{SUMMARY}}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/metwork_plugin/%{name}/ 2>/dev/null
cp -RTvf %{pwd} %{buildroot}/metwork_plugin/%{name}

%clean
rm -fr %{buildroot}

%files
%defattr(-,-,-)
/metwork_plugin

{% for EXCLUDE in EXCLUDES %}
%exclude /metwork_plugin/%{name}/{{EXCLUDE}}
{% endfor %}
