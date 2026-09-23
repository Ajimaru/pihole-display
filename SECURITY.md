# Security Policy

## Supported Versions

Only the latest release receives security fixes.

## Reporting a Vulnerability

Please do not open a public issue. Report it privately via
[GitHub Security Advisories](https://github.com/Ajimaru/pihole-display/security/advisories/new)
and include steps to reproduce and the affected version (shown in the
System screen header).

This is a hobby project maintained in spare time, so there is no fixed
response time. You will get an answer once the report has been looked at.

## Scope

pihole-display runs as root: it reads Pi-hole's local CLI password
(`/etc/pihole/cli_pw`) and can restart services, reboot and shut down the
system. Issues that let other users or the network trigger these actions are
in scope. Vulnerabilities in Pi-hole or Unbound themselves should be reported
to those projects.
