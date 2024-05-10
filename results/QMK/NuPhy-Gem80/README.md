Test setup:


**Host**: Raspberry Pi 4 running Raspberry OS version 11
**Keyboard**: NuPhy Gem80 (tri-mode) connected via USB-C

**Keyboard Firmwares tested**:

- Official firmware for Gem80 (tri-mode) (QMK) v1.1.4 from [NuPhy's website](https://nuphy.com/pages/qmk-firmwares)
    - tested in default configuration - debounce value unknown, algorithm unknown

- Official firmware for Gem80 (tri-mode) (QMK) v2.0.1 from [NuPhy's website](https://nuphy.com/pages/qmk-firmwares)
    - tested in default configuration - debounce value unknown, algorithm unknown

- Custom firmware (QMK) from [ryodeushii](https://github.com/ryodeushii/qmk-firmware/releases/tag/ryo-1.1.0.2)
    - tested in default configuration (asym_eager_defer 5ms press, 5ms release)
    - tested in adjusted configuration (asym_eager_defer 3ms press, 3ms release)

- Custom firmware (QMK) from [ryodeushii](https://github.com/ryodeushii/qmk-firmware/releases/tag/ryo-1.1.1)
    - tested in default configuration (asym_eager_defer 5ms press, 5ms release)
    - tested in adjusted configuration (asym_eager_defer 3ms press, 3ms release)

