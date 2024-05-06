<h1 align="center">
  <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Assets/logo.png" alt="HellFire Logo">
</h1>

<h2 align="center">
  <img src="https://img.shields.io/badge/-HellFire-61DAFB?logo=firefox&logoColor=white&style=for-the-badge" alt="Product: HellFire">&nbsp;
  <img src="https://img.shields.io/badge/-MPLv2.0-61DAFB?style=for-the-badge" alt="License: MPLv2.0">&nbsp;
  <img src="https://img.shields.io/badge/-127.0a1-61DAFB?style=for-the-badge" alt="Version: 127.0a1">
</h2>

**HellFire**, named after the [HellFire Air-To-Surface missile](https://en.wikipedia.org/wiki/AGM-114_Hellfire), is a Firefox build optimized for absolute performance. It's a direct compilation of Firefox, emphasizing maximum performance without any source, configuration, or visual modifications.

## Releases

We provide builds for both Windows x64 and Linux x64 platforms.

- **Windows x64 Builds**: [Releases](https://github.com/CYFARE/HellFire/releases/)
- **Linux x64 Builds**: [Releases](https://github.com/CYFARE/HellFire/releases/)

## Benchmarks

Higher score = Faster browser. Hellfire 127 outperformed both ungoogled-chromium and forked-optimized Mercury browser! 

<h2 align="center">
  <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Benchmarks/score.png" alt="Benchmarks">
</h2>

You don't need to have a shady easter-egg inside forked sources.. just download & use HellFire :)

## Compile Time Optimizations

HellFire offers a variety of optimized builds, each tailored for different levels of optimization and security.

| Configuration          | Optimization and Security Settings                     | Description                                            |
|------------------------|--------------------------------------------------------|--------------------------------------------------------|
| HellFire Lazer         | `-O3` Optimized with Default Security                  | Fast + Default Security, based on Mozilla's default compile |
| HellFire Missile       | `-Ofast` Optimized with Reduced Security               | Super Fast + Less Secure                               |
| HellFire Tracker       | `-Ofast` Optimized with Reduced Security + Debugging   | Super Fast + Less Secure + For Debugging Purposes      |

For more details, explore our Mozconfigs:
- [Win64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Win64)
- [Linux64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Linux64)

To build your own version, follow the [Firefox Build Guide](https://firefox-source-docs.mozilla.org/setup/). Ensure you copy the desired mozconfig to `mozilla-unified` and rename it to `mozconfig` before running `./mach build`.

> For custom builds like 'hardened' or mixed flag builds, please contact us directly.

## Install & Update HellFire

Stay updated with the latest versions and installer on our [Releases](https://github.com/CYFARE/HellFire/releases/) page.

- Windows installer exe will automatically upgrade/update the existing install without removing/changing your bookmarks or settings :)
- For GNU/Linux, check the following:

1) Download preferred 7z package of HellFire from releases (7z packages are offered starting from v127.0a1). 
2) Download hellfire_installer.sh script from releases.
3) `cd ~/ && Downloads && sudo chmod +x hellfire_installer.sh && ./hellfire_installer.sh`

- If you're using Ubuntu or Ubuntu based OS like Zorin/Mint etc., then check your application menu & HellFire shortcut will be there.
- You can also run HellFire from terminal using: `hellfire` command.
- You can pipe hellfire through proxychains for using with proxies or tor using: `proxychains hellfire`
- For updating to new version, just follow same steps & installer script will update your hellfire browser without editing your bookmarks, extensions or settings :)


## Self Compile

Download the mozconfig for your preferred HellFire build from [HellFire MozConfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs), rename it to 'mozconfig', place it under mozilla-unified, and begin your build.

## Support

Enjoying HellFire's performance boost? Consider supporting us via UPI (India only). Please add a note for 'HellFire Support' when donating. Thank you for your support!

For UPI details, contact us via the email provided below.

## Ethics

For insights into our project's ethos, please read our [Ethics Statement](https://raw.githubusercontent.com/CYFARE/HellFire/main/ETHICS.md).

## Contact

Feel free to reach out at:

`murgimasalatikka[@]gmail[.]com`
