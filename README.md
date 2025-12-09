<h1 align="center">
  <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Assets/logo.png" alt="HellFire Logo">
</h1>

<h2 align="center">
  <img src="https://img.shields.io/badge/-HellFire-61DAFB?logo=firefox&logoColor=white&style=for-the-badge" alt="Product: HellFire">&nbsp;
  <img src="https://img.shields.io/badge/-MPLv2.0-61DAFB?style=for-the-badge" alt="License: MPLv2.0">&nbsp;
  <img src="https://img.shields.io/badge/-148.0a1-61DAFB?style=for-the-badge" alt="Version: 148.0a1">
</h2>

**HellFire**, named after the [HellFire Air-To-Surface missile](https://en.wikipedia.org/wiki/AGM-114_Hellfire), is a Firefox build optimized for absolute performance. It's a direct compilation of Firefox, emphasizing maximum performance without any source, configuration, or visual modifications.

## Releases

We provide x86_64 builds for both GNU/Linux.

- **x86_64 GNU/Linux**: [Releases](https://github.com/CYFARE/HellFire/releases/)

Note: Windows builds failing consistently. Microsoft Windows has been the single most bugged and worst system for developers and it's users. Due to consistent issues exclusive to Windows, Microsoft Windows is removed from support completely, with immediate effect.

As Linus Torvalds said to NVIDIA once, I say to Microsoft - **--- YOU MICROSOFT**

## Benchmarks

Higher score = Faster browser. Hellfire 144 outperforms Firefox mainline and Ungoogled Chromium.

<h2 align="center">
 <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Benchmarks/chart.png">
</h2>

<h6 align="center">

| Benchmark       | HellFire 144.0a1 | Ungoogled Chromium | Firefox 142.0.1 |
|-----------------|------------------|--------------------|-----------------|
| Speedometer 3.1 | 20.9327          | 20.2244            | 19.9420         |

</h6>

You don't need to have a shady easter-egg inside forked sources.. just download & use HellFire :)

## Compile Time Optimizations

HellFire offers a variety of optimized builds, each tailored for different levels of optimization and security.

| Configuration          | Optimization and Security Settings                     | Description                                            |
|------------------------|--------------------------------------------------------|--------------------------------------------------------|
| HellFire (GNU/Linux)         | `-O3` Optimized, Hardened Security, Sandbox Enabled                  | AVX2 + SSE4.2 + Full LTO |


For more details, explore our Mozconfigs:

- [Linux64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Linux64)

To build your own version, follow the [Firefox Build Guide](https://firefox-source-docs.mozilla.org/setup/). Ensure you copy the desired mozconfig to `mozilla-unified` and rename it to `mozconfig` before running `./mach build`.

> For custom builds like 'hardened', 'Insecure' or mixed flag builds, please contact via: security@cyfare.net

## Install & Update HellFire

Stay updated with the latest versions and installer on our [Releases](https://github.com/CYFARE/HellFire/releases/) page.

For GNU/Linux, you can either install <a href='https://github.com/CYFARE/HellFire/releases/'><img src="https://img.shields.io/badge/-FLATPAK-61DAFB?style=for-the-badge"></a> or follow the below process:

1) Make sure to have following packages: `sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1`
2) Download and run `python linux_installer.py`

Legacy installer (incase of issues):

1) Download preferred 7z package of HellFire from releases (7z packages are offered starting from v127.0a1).
2) Download hellfire_installer.sh script from older releases
3) `cd ~/ && cd Downloads && sudo chmod +x hellfire_installer.sh && ./hellfire_installer.sh`

If you're using Ubuntu or Ubuntu based OS like Zorin/Mint etc., then check your application menu & HellFire shortcut will be there. You can also run HellFire from terminal using: `hellfire` command. You can pipe hellfire through proxychains for using with proxies or tor using: `proxychains hellfire`

For updating to new version on GNU/Linux, just follow same steps & installer script will update your hellfire browser without editing your bookmarks, extensions or settings :)

## Self Compile

Download the mozconfig for your preferred HellFire build from [HellFire MozConfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs), rename it to 'mozconfig', place it under mozilla-unified, and begin your build.

## Support

Enjoying HellFire's performance boost? Consider supporting us via UPI (India only). Please add a note for 'HellFire Support' when donating. Thank you for your support!

For UPI details, contact us via the email provided below.

## Ethics

For insights into our project's ethos, please read our [Ethics Statement](https://raw.githubusercontent.com/CYFARE/HellFire/main/ETHICS.md).






