---
name: Bug report
about: Report a problem with the display, buttons or shown data
title: ''
labels: bug
assignees: ''

---

<!-- Security issues: please do not report them here, see SECURITY.md. -->

## Describe the bug

What is wrong? E.g. wrong value on a screen, button does nothing, service
crashes.

## To reproduce

1. Screen / menu: [e.g. System → Screen lock]
2. Buttons pressed: [e.g. # short, then ^]
3. What happens:

## Expected behavior

What should have happened instead.

## Photo or screenshot

If it is a display problem, a photo of the OLED helps.

## Environment

- pihole-display version: [shown in the System screen header, e.g. v0.0.1]
- Board: [e.g. BeagleBone Black]
- OS / kernel: [output of `cat /etc/os-release | head -1` and `uname -r`]
- Pi-hole version: [output of `pihole -v`]
- Unbound version: [output of `sudo unbound -V | head -1`, or "not used"]
- Display: [e.g. SSD1315, I2C address 0x3C]

## Service log

Output of `sudo journalctl -u pihole-display -n 50 --no-pager`:

```text
paste log here
```

## Changes to config.py

Anything changed from the defaults (leave out passwords).

## Additional context

Anything else, e.g. custom wiring or a different case.
