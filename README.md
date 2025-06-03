<h1 align="center">
  <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Assets/logo.png" alt="HellFire Logo">
</h1>

<h2 align="center">
  <img src="https://img.shields.io/badge/-HellFire-61DAFB?logo=firefox&logoColor=white&style=for-the-badge" alt="Product: HellFire">&nbsp;
  <img src="https://img.shields.io/badge/-MPLv2.0-61DAFB?style=for-the-badge" alt="License: MPLv2.0">&nbsp;
  <img src="https://img.shields.io/badge/-141.0a1-61DAFB?style=for-the-badge" alt="Version: 141.0a1">
</h2>

**HellFire**, named after the [HellFire Air-To-Surface missile](https://en.wikipedia.org/wiki/AGM-114_Hellfire), is a Firefox build optimized for absolute performance. It's a direct compilation of Firefox, emphasizing maximum performance without any source, configuration, or visual modifications.

## Releases

We provide x86_64 builds for both GNU/Linux and Windows platforms.

- **x86_64 GNU/Linux and Windows Builds**: [Releases](https://github.com/CYFARE/HellFire/releases/)

## Benchmarks

Higher score = Faster browser. Hellfire 127 and later outperforms both ungoogled-chromium and forked-optimized Mercury browser!

<h2 align="center">
 <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Benchmarks/chart.png">
</h2>

<h6 align="center">

| Benchmark | HellFire Lazer 129 | Mercury 123 - Thorium |
|------------------|---------------------|-------------------|
| Speedometer 2.1  | 387                 | 345               |
| Octane 2.1       | 50971               | 51782             |
| JetStream 2      | 222.982             | 215.101           |

</h6>

You don't need to have a shady easter-egg inside forked sources.. just download & use HellFire :)

## Compile Time Optimizations

HellFire offers a variety of optimized builds, each tailored for different levels of optimization and security.

| Configuration          | Optimization and Security Settings                     | Description                                            |
|------------------------|--------------------------------------------------------|--------------------------------------------------------|
| HellFire (GNU/Linux)         | `-O3` Optimized, Hardened Security, Sandbox Enabled                  | AVX2 + SSE4.2 + Full LTO |
| HellFire (Windows)         | `-O3` Optimized, Hardened Security, Sandbox Enabled                  | AVX2 + SSE4.2 |

For more details, explore our Mozconfigs:

- [Linux64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Linux64)
- [Win64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Win64)

To build your own version, follow the [Firefox Build Guide](https://firefox-source-docs.mozilla.org/setup/). Ensure you copy the desired mozconfig to `mozilla-unified` and rename it to `mozconfig` before running `./mach build`.

> For custom builds like 'hardened', 'Insecure' or mixed flag builds, please contact via: security@cyfare.net

## Install & Update HellFire

Stay updated with the latest versions and installer on our [Releases](https://github.com/CYFARE/HellFire/releases/) page.

Windows installer exe will automatically upgrade/update the existing install without removing/changing your bookmarks or settings :)

For GNU/Linux, check the following:

1) Download preferred 7z package of HellFire from releases (7z packages are offered starting from v127.0a1).
2) Download hellfire_installer.sh script from releases.
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
