![Product](https://img.shields.io/badge/-HellFire-61DAFB?logo=firefox&logoColor=white&style=for-the-badge) &nbsp;![License](https://img.shields.io/badge/-The%20Unlicense-61DAFB?logo=license&logoColor=white&style=for-the-badge) &nbsp;![Version](https://img.shields.io/badge/-123.0a1-61DAFB?logo=version&logoColor=white&style=for-the-badge)

<p align="center">
  <img src="https://raw.githubusercontent.com/BVSHAI/HellFire/main/Assets/logo.png">
</p>

**HellFire** ( named after [HellFire Air-To-Surface missile](https://en.wikipedia.org/wiki/AGM-114_Hellfire) ) is a highly optimized Firefox build that prioritizes absolute performance. It is a 1:1 compile without any source, configuration or visual changes. Just pure Firefox compiled for maximum performance.

## Releases

Only Windows builds are provided for now.

- [Releases](https://github.com/BVSHAI/HellFire/releases/)

## Compile Time Optimizations

- Enable -O3 optimization CFLAGS
- Enable Rust language -O3 optimizations
- Disable debug mode to avoid performance penalties
- Enable link-time optimization (LTO) for better performance
- Enable JE malloc
- Disable Updater for performance
- Disable Crash Reporter for performance
- Disable Debug symbols for performance
- Disable Maintenance Service for performance
- Disable parental controls for performance
- Reduce the binary size by stripping symbols
- Specify the Profile-Guided Optimization (PGO)

## Security

- As secure as original Firefox browser due to this being 1:1 identical build
- No security features are added or removed
- Patch state matches that of the latest Nightly branch

## Updates

- Check for latest updates on [Releases](https://github.com/BVSHAI/HellFire/releases/) page. You may use the provided installer.

## Self Compile?

Please see this [mozconfig](https://raw.githubusercontent.com/BVSHAI/HellFire/main/mozconfig) file if you wish to compile with the same optimizations :)

## Support?

If you like the huge performance improvements this provides, please consider supporting me via UPI (India only) and do write a note for 'HellFire Support'. Thanks for using this build!

<p align="center">
  <img src="https://raw.githubusercontent.com/BVSHAI/HellFire/main/Assets/support_upi.png">
</p>

## Ethics

Please view the [Ethics Statement](https://raw.githubusercontent.com/BVSHAI/HellFire/main/ETHICS.md) for better clarity on project and communication with developers.

## Contact

Reach me out at:
`murgimasalatikka[@]gmail[.]com`
