<h1 align="center">
  <img src="https://raw.githubusercontent.com/CYFARE/HellFire/main/Assets/logo.png" alt="HellFire Logo">
</h1>

<h2 align="center">
  <img src="https://img.shields.io/badge/-HellFire-61DAFB?logo=firefox&logoColor=white&style=for-the-badge" alt="Product: HellFire">&nbsp;
  <img src="https://img.shields.io/badge/-MPLv2.0-61DAFB?style=for-the-badge" alt="License: MPLv2.0">&nbsp;
  <img src="https://img.shields.io/badge/-152.0a1-61DAFB?style=for-the-badge" alt="Version: 152.0a1">
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

HellFire offers the following optimizations over regular Firefox or Nighly build:

| # | Category | Improvement |
|---|----------|-------------|
| 1 | Graphics | WebRender force-enabled |
| 2 | Graphics | Hardware canvas acceleration |
| 3 | Graphics | Wayland / X11-EGL / DMABUF force-enabled |
| 4 | Graphics | GPU process + MLGPU forced on |
| 5 | Graphics | Unlocked frame rate |
| 6 | Graphics | WebGL / WebGPU unlocked |
| 7 | Graphics | GfxInfo blocklist neutered |
| 8 | Media | VA-API hardware video decode |
| 9 | Media | AV1 via dav1d + ffvpx-hw |
| 10 | Media | Enlarged media caches |
| 11 | Media | Low-latency ffmpeg decode |
| 12 | JS Engine | Aggressive JIT thresholds |
| 13 | JS Engine | WebAssembly SIMD + relaxed SIMD |
| 14 | JS Engine | Spectre mitigations disabled |
| 15 | JS Engine | Ion inlining limits raised |
| 16 | JS Engine | GC tuning (parallel marking, compacting) |
| 17 | Memory | mozjemalloc arenas doubled |
| 18 | Memory | mozjemalloc dirty-page retention increased |
| 19 | Cache | Larger memory + disk cache |
| 20 | Networking | HTTP/3 + 0-RTT |
| 21 | Networking | Raised connection limits |
| 22 | Networking | Expanded DNS cache |
| 23 | Networking | Early Hints + predictor |
| 24 | Networking | TCP Fast Open |
| 25 | Networking | SSL token cache enlarged |
| 26 | Networking | HTTP pacing disabled |
| 27 | Parser | Reduced paint latency |
| 28 | Parser | Parser interrupt disabled |
| 29 | IPC | Tuned content process count |
| 30 | IPC | Fission autostart + bytecode cache |
| 31 | Startup | PreXUL skeleton UI + blank window |
| 32 | Startup | Cosmetic animations disabled |
| 33 | Startup | Speculative connect on urlbar/places |
| 34 | Session | Reduced sessionstore disk I/O |
| 35 | Telemetry | All telemetry/reporting killed |
| 36 | Build | Pocket + Normandy stripped |
| 37 | Build | Full LTO + PGO |
| 38 | Build | LLD linker |
| 39 | Build | Rust SIMD + WASM AVX |
| 40 | Build | x86-64-v3 target + AES |
| 41 | Build | Aggressive Rust codegen |
| 42 | Build | Aggressive C/C++ flags |
| 43 | Build | Linker hardening + size reduction |
| 44 | Build | Debug/tests/crashreporter/updater disabled |
| 45 | Build | Hardened sandbox + replace-malloc |
| 46 | Build | Parallel compilation |
| 47 | Accessibility | a11y subsystem disabled |
| 48 | Tooling | Reversible patch system |

For more details, explore our Mozconfigs and hellfire_patcher:

- [Linux64 Mozconfigs](https://github.com/CYFARE/HellFire/tree/main/MozConfigs/Linux64)
- [Hellfire Patcher](https://github.com/CYFARE/HellFire/tree/main/hellfire_patcher.sh)

To build your own version, follow the [Firefox Build Guide](https://firefox-source-docs.mozilla.org/setup/). Ensure you copy the desired mozconfig to `mozilla-unified` and rename it to `mozconfig`, run `chmod +x hellfire_patcher.sh && ./hellfire_patcher.sh --apply` before running `./mach build`.

> For custom builds like 'hardened', 'Insecure' or mixed flag builds, please contact via: security@cyfare.net

## Install & Update HellFire

Stay updated with the latest versions and installer on our [Releases](https://github.com/CYFARE/HellFire/releases/) page.

For GNU/Linux, follow the below process:

### Package Installation

```bash
sudo apt-get update && sudo apt-get install -y python3 python3-tk python3-requests python3-pil
```

Run the installer using:

```bash
python3 hellfire_installer.py
```

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







