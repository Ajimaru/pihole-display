# Third-Party Licenses

This project uses the following open-source libraries:

---

## luma.oled

- **Repository:** [https://github.com/rm-hull/luma.oled](https://github.com/rm-hull/luma.oled)
- **License:** MIT
- **Copyright:** Richard Hull and contributors
- **Used for:** OLED display driver (SSD1306 / SSD1315)

---

## Pillow

- **Repository:** [https://github.com/python-pillow/Pillow](https://github.com/python-pillow/Pillow)
- **Website:** [https://python-pillow.org/](https://python-pillow.org/)
- **License:** MIT-CMU
- **Copyright:** Jeffrey A. Clark and contributors
- **Used for:** Text and graphics rendering on the OLED canvas

---

## psutil

- **Repository:** [https://github.com/giampaolo/psutil](https://github.com/giampaolo/psutil)
- **License:** BSD 3-Clause
- **Copyright:** Jay Loden, Dave Daeschler, Giampaolo Rodola
- **Used for:** System statistics (CPU, RAM, disk, uptime, temperature)

---

## requests

- **Repository:** [https://github.com/psf/requests](https://github.com/psf/requests)
- **Website:** [https://docs.python-requests.org/](https://docs.python-requests.org/)
- **License:** Apache License 2.0
- **Copyright:** Kenneth Reitz and contributors
- **Used for:** Pi-hole REST API calls (v5 and v6)

---

## python-gpiod (libgpiod Python bindings)

- **Repository:** [https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/](https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/)
- **License:** LGPL-2.1-or-later
- **Copyright:** Bartosz Golaszewski and contributors
- **Used for:** GPIO input reading for hardware buttons on BeagleBone Black

---

## luma.core

- **Repository:** [https://github.com/rm-hull/luma.core](https://github.com/rm-hull/luma.core)
- **License:** MIT
- **Copyright:** Richard Hull and contributors
- **Used for:** Core rendering abstraction (pulled in by luma.oled)

---

## smbus2

- **Repository:** [https://github.com/kplindegaard/smbus2](https://github.com/kplindegaard/smbus2)
- **License:** MIT
- **Copyright:** Karl-Petter Lindegaard
- **Used for:** I2C communication (pulled in by luma.oled)

---

## Inspiration / Reference Projects

The following open-source projects were used as reference during development
(no code was copied):

- **willdurand/pihole-oled** [https://github.com/willdurand/pihole-oled](https://github.com/willdurand/pihole-oled) - MIT
- **faithvoid/PiHOLED** [https://github.com/faithvoid/PiHOLED](https://github.com/faithvoid/PiHOLED) - MIT
- **Maschine2501/PiHole-UI** [https://github.com/Maschine2501/PiHole-UI](https://github.com/Maschine2501/PiHole-UI) - MIT
