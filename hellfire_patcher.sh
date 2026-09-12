#!/usr/bin/env bash
# hellfire_patcher.sh  —  Performance patch set for HellFire / Firefox on GNU/Linux
#
# Usage:
#   cd mozilla-unified
#   ./hellfire_patcher.sh --apply                          # public profile (default)
#   HELLFIRE_PROFILE=bench ./hellfire_patcher.sh --apply   # kitchen sink, your box only
#   ./hellfire_patcher.sh --revert         # before `git pull` / `hg pull`
#   ./hellfire_patcher.sh --status
#   ./hellfire_patcher.sh --check-prefs    # audit pref names against THIS tree
#   ./hellfire_patcher.sh --help
#
# Profiles (HELLFIRE_PROFILE, default "public"):
#   public  what you ship. Every compile-time and pref-level speed change that
#           does not trade a stranger's safety, accessibility or driver
#           stability for a number: no Spectre/timer changes, a11y untouched,
#           no blocklist bypass / *.force-enabled, widget/GfxInfo.cpp left alone.
#   bench   public + the force-enable / blocklist-bypass prefs, Spectre and
#           timer precision off, a11y + spellcheck off, and section B.
#           For the machine you run Speedometer on, not for a package.
#
# Design:
#   Each patch backs the original file up to .hellfire_backup/<path> before
#   modifying it, and records the path in .hellfire_applied. --revert copies
#   every backed-up file back into place and clears the state, leaving the
#   working tree identical to pre-apply. Safe for git/hg pulls.
#
# Patches are grouped:
#   A. Runtime prefs (appended as a single block to browser/app/profile/firefox.js)
#   B. Graphics blocklist neutering (widget/GfxInfo.cpp, Linux section)  [bench only]
#   C. Allocator tuning (memory/build/mozjemalloc.cpp)
#   D. Ion JIT inlining constants (js/src/jit/JitOptions.cpp)
#   E. retired in v2.2 (see changelog)
#   F. PGO training-corpus extension (build/pgo/index.html)
#
# Safe to re-run --apply after --revert. Safe to run --revert repeatedly.
#
# ── v2.0 changelog ───────────────────────────────────────────────────────────
# Pref block rebuilt and verified against a Firefox 152 (152.0.6) about:config
# dump. Every pref in section A is confirmed to EXIST in FF152; 54 dead prefs
# were removed, 14 no-op pins dropped, and 9 values that were *slower than
# stock* were fixed:
#   • dom.script_loader.bytecode_cache.strategy -1 → 1
#       (see v2.2 — this one is now believed to have been backwards)
#   • javascript.options.mem.gc_incremental_slice_ms 100 → 10
#       (100 ms GC slices = guaranteed frame-eating pauses; stock is 5 ms)
#   • gfx.canvas.accelerated.cache-items 4096 → 16384   (stock is 8192)
#   • image.cache.size 10 MB → 256 MB                   (stock is 20 MB)
#   • network.http.keep-alive.timeout 60 → 300          (stock is 115)
#   • layout.throttled_frame_rate 60 → 1  (don't render hidden tabs at 60 fps)
#   • browser.cache.jsbc_compression_level 3 → 0  (compression tax on reads)
#   • javascript.options.mem.gc_low_frequency_heap_growth 110 → 200 (stock 150)
#   • browser.sessionstore.idleDelay dropped (units changed upstream; 180000
#     would have been nonsense)
# New live extremes added: HTTP/3 recv buffer 8 MB, happy eyeballs,
# prefetch-next, hover preconnect, DNS prefetch for HTTPS anchors, surface
# cache retention 5 min, WebGPU blocklist bypass + external-texture, 8
# parallel GC marking threads, Ion inline bytecode length 140 → 200,
# forkserver / tab-warmup pins, webIsolated procs 4 → 8.
# The GPU process is no longer force-enabled on Linux: it is upstream-disabled
# for stability, WebRender already runs hardware-accelerated in the parent
# process, and forcing it adds IPC overhead + crash surface for no fps gain.
#
# ── v2.1 changelog (audited against mozilla-central tip / FF155) ─────────────
#   • REMOVED javascript.options.asmjs — asm.js was removed from SpiderMonkey;
#     the pref no longer exists anywhere in the tree.
#   • browser.tabs.remote.warmup.enabled KEPT — an early draft of this audit
#     checked only StaticPrefList.yaml/all.js and missed that it is defined in
#     stock firefox.js (default true, with warmup.maxTabs / unloadDelayMs).
#     Retained as a drift pin. Lesson baked into --check-prefs: it scans
#     stock firefox.js (block-stripped) in addition to libpref + code.
#   • REMOVED javascript.options.spectre.jit_to_cxx_calls — already false at
#     stock on 155 (no-op pin, per v2.0 housekeeping rules).
#   • Spectre section re-annotated: FF155 ships
#     javascript.options.spectre.disable_for_isolated_content = true by
#     default, so content processes (where benchmarks run) already skip these
#     mitigations at stock. The pref is explicitly pinned true in case a
#     distro/ESR base flips it.
#   • javascript.options.mem.nursery.max_kb comment corrected: stock on 155 is
#     already 65536 — the pin is kept only as drift protection.
#   • NEW section F: doubles Speedometer 3 coverage in the PGO training corpus
#     (build/pgo/index.html). With MOZ_PGO=1 the profileserver already runs
#     one auto-started SP3 pass; this adds a second one.
#   • NEW command --check-prefs: one tree scan that reports every pref in
#     section A with no definition or code reference on the CURRENT tree.
#     Run it after every pull — 152→155 drift already produced two dead prefs.
#
# ── v2.2 changelog ───────────────────────────────────────────────────────────
#   • NEW: HELLFIRE_PROFILE=public|bench (default public). The public block is
#     what goes into a build you hand to strangers; the bench block is
#     appended on top for your own machine. --status shows which was applied.
#   • MOVED to the bench block: gfx.webrender.all, every *.force-enabled,
#     gfx.webgpu.ignore-blocklist, dom.webgpu.* (add back to public once
#     Mozilla ships WebGPU by default on Linux — then it is a no-op),
#     webgl.force-enabled / msaa-force / enable-draft-extensions /
#     disable-fail-if-major-performance-caveat, the four global
#     javascript.options.spectre.* off-pins, privacy.reduceTimerPrecision,
#     accessibility.force_disabled, layout.spellcheckDefault.
#     Why: the Spectre pins buy nothing on a benchmark (isolated content
#     already skips the mitigations at stock — the v2.1 note above), so a
#     public build would pay the security cost for zero score. Force-enable /
#     blocklist-bypass prefs only help on hardware Mozilla's blocklist is too
#     conservative about and crash or glitch on hardware it is right about; a
#     shipped build cannot know which machine it landed on. a11y is only
#     instantiated when an AT client connects, so force_disabled costs
#     non-AT users nothing and only affects the people it breaks.
#   • FIXED image.mem.surfacecache.size_factor: the surface-cache budget is
#     physical_RAM / size_factor (SurfaceCache::Initialize), so 8 HALVED the
#     budget instead of doubling it. Pin dropped; image.mem.surfacecache.
#     max_size_kb raised to 4 GB instead, which only changes anything on
#     machines with >= 16 GB and never exceeds RAM/4.
#   • DROPPED the dom.script_loader.bytecode_cache.strategy pin. In the
#     ScriptLoader::ShouldCacheBytecode switch as I know it, -1 is the "eager
#     mode, skip heuristics" branch (it is what Mozilla's own tests set to
#     force caching) and 1 falls through to the default heuristic — the
#     opposite of the v2.0 note. Verify on your tree:
#         grep -n -A3 'case -1' dom/script/ScriptLoader.cpp
#     If -1 is eager, add  pref("dom.script_loader.bytecode_cache.strategy", -1);
#     to the BENCH block only: eager caching is right for repeated-load
#     benchmarks, the heuristic is right for users (it avoids writing bytecode
#     for every script seen once).
#   • DROPPED network.http.speculative-parallel-limit = 10 — stock is 20; the
#     pin was a downgrade.
#   • DROPPED dom.ipc.processPrelaunch.lowmem_mb = 0 — stock 4096 means "do not
#     keep spare content processes warm when free RAM is under 4 GB", which is
#     exactly the heuristic a public build wants.
#   • DROPPED browser.startup.preXulSkeletonUI / browser.startup.blankWindow:
#     Windows-only code paths, inert on Linux.
#   • MODERATED RAM/bandwidth-scaling values that do not move any benchmark
#     (all still far above stock): browser.cache.memory.capacity 1 GB → 256 MB,
#     max_entry_size 256 → 64 MB, media.memory_cache_max_size 1 GB → 128 MB,
#     media.memory_caches_combined_limit_kb 2.5 → 1 GB, media.cache_readahead_
#     limit 9999 → 600 s, media.cache_resume_threshold 3600 → 300 s,
#     network.dnsCacheExpiration 3600 → 600 s (an hour of stale DNS makes a
#     CDN fail-over look like an outage; Linux builds do not honour TTLs).
#   • RETIRED section E (Pocket/Normandy DIRS strip). Pocket is gone from the
#     tree. Commenting out the normandy DIRS entry while MOZ_NORMANDY stays
#     defined leaves BrowserGlue's resource://normandy/ import dangling, and a
#     one-line `if CONFIG["MOZ_NORMANDY"]: DIRS += [...]` becomes a moz.build
#     syntax error. app.normandy.enabled=false already makes it inert.
#   • Section B now only wraps entries whose status is FEATURE_BLOCKED_* /
#     FEATURE_DISCOURAGED / FEATURE_DENIED. FEATURE_ROLLOUT_* entries are
#     ALLOW rules; neutering them would have turned features OFF. Bench only.
#   • Section F uses extendedTimeout when the tree does not define
#     superExtendedTimeout — an undefined identifier there throws at page
#     load and silently degrades the whole PGO training run.
#   • --check-prefs matches whole names ("name" string literals, YAML `name:`
#     fields, pref() lines) instead of substrings, so a dead pref that is a
#     prefix of a live one (gfx.webrender.compositor vs …compositor.
#     force-enabled) is no longer reported as alive.
#   • --apply refuses to run over a stale .hellfire_backup/ with no state file
#     (files would be modified but never recorded, so --revert would miss them).
#   • Help: with MOZ_PGO=1 in mozconfig, ./mach build runs all three PGO stages
#     itself; the old "run an instrumented pass first" note was wrong.

set -euo pipefail

# ───────────────────────────── config / tty ──────────────────────────────────
SCRIPT_VERSION="2.2"
STATE_FILE=".hellfire_applied"
BACKUP_DIR=".hellfire_backup"
MARK_START="// >>> HELLFIRE_PATCH_START - do not edit between markers"
MARK_END="// <<< HELLFIRE_PATCH_END"
PROFILE="${HELLFIRE_PROFILE:-public}"

if [[ -t 1 ]]; then
    RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'; DIM=$'\e[2m'; RST=$'\e[0m'
else
    RED=""; GRN=""; YLW=""; BLU=""; DIM=""; RST=""
fi

log()  { printf '%s[hellfire]%s %s\n' "$BLU" "$RST" "$*"; }
ok()   { printf '%s[hellfire]%s %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '%s[hellfire]%s %s\n' "$YLW" "$RST" "$*" >&2; }
err()  { printf '%s[hellfire]%s %s\n' "$RED" "$RST" "$*" >&2; }

# ───────────────────────────── helpers ───────────────────────────────────────
verify_tree() {
    if [[ ! -f mach ]] || [[ ! -d modules/libpref ]]; then
        err "Run this from the root of your mozilla-unified checkout."
        exit 1
    fi
}

backup_file() {
    # backup_file <path>  — copies file to $BACKUP_DIR/<path> if not already there
    local f="$1"
    if [[ ! -f "$f" ]]; then
        warn "skip (missing): $f"
        return 1
    fi
    local b="$BACKUP_DIR/$f"
    if [[ ! -f "$b" ]]; then
        mkdir -p "$(dirname "$b")"
        cp -p "$f" "$b"
        echo "$f" >> "$STATE_FILE"
    fi
    return 0
}

# ────────────────────────── A. runtime prefs ─────────────────────────────────
apply_prefs() {
    local f="browser/app/profile/firefox.js"
    backup_file "$f" || return 0

    log "A. appending performance pref defaults to $f  (profile: $PROFILE)"

    printf '\n%s\n// hellfire v%s profile=%s\n' "$MARK_START" "$SCRIPT_VERSION" "$PROFILE" >> "$f"

    # ── A.1 public block: everything that is safe to hand to strangers ──────
    cat >> "$f" <<'EOF'
// ════════════════════════════════════════════════════════════════════════
//  WebRender / compositor / canvas — Linux GPU path
//  (gfx.webrender.all and every *.force-enabled live in the bench block)
// ════════════════════════════════════════════════════════════════════════
pref("gfx.webrender.compositor", true);
pref("gfx.webrender.precache-shaders", true);
pref("gfx.webrender.program-binary-disk", true);
pref("gfx.webrender.software", false);
pref("gfx.webrender.max-shared-surface-size", 4096);
pref("gfx.webrender.batched-texture-uploads", true);
pref("gfx.webrender.allow-partial-present-buffer-age", true);
pref("gfx.canvas.accelerated", true);
pref("gfx.canvas.accelerated.cache-items", 16384);   // stock 8192
pref("gfx.canvas.accelerated.cache-size", 512);      // MB, stock 256
pref("gfx.canvas.accelerated.async-present", true);
pref("gfx.content.skia-font-cache-size", 80);        // MB, stock 5
pref("widget.dmabuf-webgl.enabled", true);
pref("widget.wayland.fractional-scale.enabled", true);
pref("widget.wayland.vsync.enabled", true);
pref("layers.offmainthreadcomposition.async-animations", true);
pref("layers.async-pan-zoom.enabled", true);
pref("layers.async-video.enabled", true);
pref("layout.frame_rate", -1);
pref("layout.throttled_frame_rate", 1);              // hidden tabs tick at 1 fps
// GPU process: deliberately NOT forced. On Linux it is upstream-disabled for
// stability; WebRender is already hardware-accelerated in the parent process,
// so a GPU process only adds IPC overhead and crash surface. Re-check the
// stock value after pulls: --check-prefs verifies names, not values.
pref("layers.gpu-process.enabled", false);
pref("layers.gpu-process.force-enabled", false);

// ════════════════════════════════════════════════════════════════════════
//  Image decode / surface cache
// ════════════════════════════════════════════════════════════════════════
pref("image.cache.size", 268435456);                 // 256 MB (stock 20 MB)
pref("image.cache.factor2.threshold-surfaces", 32);
pref("image.mem.decode_bytes_at_a_time", 131072);
// Surface-cache budget = physical_RAM / image.mem.surfacecache.size_factor
// (SurfaceCache::Initialize), capped by max_size_kb. v2.0's size_factor=8
// HALVED the budget; the pin is gone and the cap is raised instead, which
// only changes anything on >= 16 GB machines.
pref("image.mem.surfacecache.max_size_kb", 4194304); // 4 GB cap (stock 2 GB)
pref("image.mem.surfacecache.min_expiration_ms", 300000); // stock 60 s → 5 min
pref("image.decode-immediately.enabled", true);
pref("image.downscale-during-decode.enabled", true);
pref("image.animated.decode-on-demand.batch-size", 6);
pref("image.animated.decode-on-demand.threshold-kb", 20480);

// ════════════════════════════════════════════════════════════════════════
//  WebGL  (force / msaa-force / draft extensions / WebGPU bypass → bench)
// ════════════════════════════════════════════════════════════════════════
pref("webgl.default-antialias", true);

// ════════════════════════════════════════════════════════════════════════
//  Hardware video decode (VA-API / AV1) + media caches
// ════════════════════════════════════════════════════════════════════════
pref("media.hardware-video-decoding.enabled", true);
pref("media.ffmpeg.encoder.enabled", true);
pref("media.ffvpx-hw.enabled", true);
pref("media.rdd-vpx.enabled", true);
pref("media.rdd-ffvpx.enabled", true);
pref("media.rdd-ffmpeg.enabled", true);
pref("media.rdd-process.enabled", true);
pref("media.utility-process.enabled", true);
pref("media.navigator.mediadatadecoder_vpx_enabled", true);
pref("media.av1.enabled", true);
pref("media.av1.use-dav1d", true);
pref("media.mediasource.enabled", true);
// Sized for a machine you don't know. None of these move a benchmark.
pref("media.memory_cache_max_size", 131072);              // KB → 128 MB (stock 8 MB)
pref("media.memory_caches_combined_limit_kb", 1048576);   // 1 GB (stock 512 MB)
pref("media.cache_readahead_limit", 600);                 // s (stock 60); 9999 buffered whole films on metered links
pref("media.cache_resume_threshold", 300);                // s (stock 30)
pref("media.cache_size", 2048000);                        // KB → 2 GB on disk (stock 500 MB)

// ════════════════════════════════════════════════════════════════════════
//  JS engine — JIT thresholds / inlining / Spectre / GC
// ════════════════════════════════════════════════════════════════════════
// A/B the two thresholds on Speedometer 3 before trusting them: Mozilla's
// 100/1500 came out of SP3 data, and a very low Ion threshold compiles
// short-lived page-load code that never amortizes its compile. JetStream-
// style long loops like it; SP3 may not.
pref("javascript.options.blinterp.threshold", 10);        // baseline interpreter
pref("javascript.options.baselinejit.threshold", 10);     // stock 100
pref("javascript.options.ion.threshold", 100);            // stock 1500
pref("javascript.options.ion.frequent_bailout_threshold", 10);
pref("javascript.options.ion.offthread_compilation", true);
pref("javascript.options.inlining_bytecode_max_length", 200); // stock 140
pref("javascript.options.parallel_parsing", true);
pref("javascript.options.wasm_baselinejit", true);
pref("javascript.options.wasm_optimizingjit", true);
pref("javascript.options.wasm_relaxed_simd", true);
pref("javascript.options.native_regexp", true);
// Spectre: FF155 ships spectre.disable_for_isolated_content = true, so
// isolated content processes — where web content and every benchmark run —
// already skip the JIT mitigations at stock. Pinned against distro/ESR bases
// that flip it. The four global off-pins live in the bench block: they only
// change parent/privileged processes, which no benchmark touches.
pref("javascript.options.spectre.disable_for_isolated_content", true);
// GC: fewer, short-pause collections; RAM traded for smoothness
pref("javascript.options.mem.gc_parallel_marking", true);
pref("javascript.options.mem.gc_max_parallel_marking_threads", 8); // stock 2
pref("javascript.options.mem.incremental_weakmap", true);
pref("javascript.options.mem.gc_compacting", true);
pref("javascript.options.mem.gc_incremental", true);
pref("javascript.options.mem.gc_incremental_slice_ms", 10);   // stock 5; NOT 100
pref("javascript.options.mem.gc_allocation_threshold_mb", 100);   // stock 27
pref("javascript.options.mem.gc_high_frequency_small_heap_growth", 300);
pref("javascript.options.mem.gc_high_frequency_large_heap_growth", 200); // stock 150
pref("javascript.options.mem.gc_low_frequency_heap_growth", 200);  // stock 150
pref("javascript.options.mem.nursery.min_kb", 4096);    // stock 256
pref("javascript.options.mem.nursery.max_kb", 65536);   // stock is now 65536 — drift pin only

// ════════════════════════════════════════════════════════════════════════
//  Memory / browser caches
// ════════════════════════════════════════════════════════════════════════
pref("browser.cache.memory.enable", true);
pref("browser.cache.memory.capacity", 262144);       // KB → 256 MB (stock auto, ≈32 MB max)
pref("browser.cache.memory.max_entry_size", 65536);  // KB → 64 MB (stock 5 MB)
pref("browser.cache.disk.enable", true);
pref("browser.cache.disk.capacity", 4194304);        // KB → 4 GB
pref("browser.cache.disk.smart_size.enabled", false);
pref("browser.cache.disk.metadata_memory_limit", 2048);
pref("browser.cache.disk.max_entry_size", 262144);
pref("browser.cache.jsbc_compression_level", 0);     // no compression tax on reads
pref("browser.sessionstore.interval", 60000);        // write session state 4x less often
pref("browser.sessionstore.interval.idle", 3600000);
pref("browser.sessionstore.restore_pinned_tabs_on_demand", true);
// browser.sessionhistory.max_total_viewers intentionally left at -1 (auto):
// it scales with physical RAM, so on a high-memory machine auto already keeps
// ~20+ pages fully alive for instant back/forward — pinning it would be a
// downgrade.

// ════════════════════════════════════════════════════════════════════════
//  Networking — HTTP/3 / HTTP2 / DNS / TLS / speculative
// ════════════════════════════════════════════════════════════════════════
pref("network.http.max-connections", 1800);
pref("network.http.max-persistent-connections-per-server", 10);
pref("network.http.max-persistent-connections-per-proxy", 32);
pref("network.http.max-urgent-start-excessive-connections-per-host", 5);
pref("network.http.pacing.requests.enabled", false);
// network.http.speculative-parallel-limit: pin dropped (was 10; stock is 20)
pref("network.http.http3.enable", true);
pref("network.http.http3.enable_0rtt", true);
pref("network.http.http3.recvBufferSize", 8388608);  // 8 MB (stock 1 MB) — high-BDP QUIC
pref("network.http.http3.enable_qlog", false);
pref("network.http.http2.enabled", true);
pref("network.http.http2.default-concurrent", 200);  // stock 100
pref("network.http.keep-alive.timeout", 300);        // stock 115
pref("network.http.happy_eyeballs_enabled", true);   // dual-stack racing
pref("network.http.network-changed.timeout", 3);
pref("network.http.referer.XOriginTrimmingPolicy", 2);
pref("network.dns.disablePrefetch", false);          // some distro builds default true
pref("network.dns.disablePrefetchFromHTTPS", false);
pref("dom.prefetch_dns_for_anchor_https_document", true); // stock false
pref("network.dnsCacheEntries", 4000);               // stock 1600
pref("network.dnsCacheExpiration", 600);             // stock 60; 3600 hid CDN fail-overs for an hour
pref("network.dnsCacheExpirationGracePeriod", 600);
pref("network.prefetch-next", true);                 // honor rel=prefetch
pref("network.predictor.enable-hover-on-ssl", true); // stock false — preconnect on hover
pref("network.preconnect", true);
pref("network.early-hints.enabled", true);
pref("network.early-hints.preconnect.enabled", true);
pref("network.early-hints.preconnect.max_connections", 10);
pref("network.ssl_tokens_cache_capacity", 10240);    // stock 8192
pref("network.buffer.cache.count", 128);             // stock 24
pref("network.buffer.cache.size", 65536);            // stock 32768
pref("network.websocket.max-connections", 2000);     // stock 200
pref("security.tls.enable_0rtt_data", true);
pref("security.ssl.enable_false_start", true);

// ════════════════════════════════════════════════════════════════════════
//  Parser / layout / paint latency
// ════════════════════════════════════════════════════════════════════════
pref("content.notify.interval", 250000);             // stock 120000 — parser yields less often
pref("content.notify.ontimer", true);
pref("content.notify.backoffcount", 5);
pref("nglayout.initialpaint.delay", 5);
pref("nglayout.initialpaint.delay_in_oopif", 5);
pref("apz.overscroll.enabled", true);
pref("apz.paint_skipping.enabled", true);
pref("mousewheel.system_scroll_override.enabled", true);
pref("general.smoothScroll", true);
pref("general.smoothScroll.msdPhysics.enabled", true);
// NOTE: the classic content.interrupt.parsing / content.max.tokenizing.time /
// content.switch.threshold trio no longer exists — FF152+ uses content.sink.*,
// whose defaults already match the old "tuned" values.

// ════════════════════════════════════════════════════════════════════════
//  Content process / fission / IPC
// ════════════════════════════════════════════════════════════════════════
pref("dom.ipc.processCount", 8);
pref("dom.ipc.processCount.webIsolated", 8);         // stock 4 — costs RAM on small machines
pref("dom.ipc.processPrelaunch.enabled", true);
pref("dom.ipc.processPrelaunch.fission.number", 3);
// dom.ipc.processPrelaunch.lowmem_mb: pin dropped; stock 4096 stops prelaunch
// on machines with < 4 GB free, which is what a public build wants.
pref("dom.ipc.forkserver.enable", true);             // fast content-proc spawn on Linux
pref("browser.tabs.remote.warmup.enabled", true);    // stock true — drift pin (tab warmup = instant tab switch)
pref("dom.enable_web_task_scheduling", true);
pref("dom.script_loader.bytecode_cache.enabled", true);
// dom.script_loader.bytecode_cache.strategy intentionally NOT pinned — see
// the v2.2 changelog for the -1 / 1 semantics question and the grep to settle it.
pref("fission.autostart", true);

// ════════════════════════════════════════════════════════════════════════
//  Startup / UI responsiveness
// ════════════════════════════════════════════════════════════════════════
pref("browser.startup.homepage_override.mstone", "ignore");
pref("browser.shell.checkDefaultBrowser", false);
pref("browser.aboutwelcome.enabled", false);
pref("browser.tabs.remote.useCrossOriginOpenerPolicy", true);
pref("browser.tabs.remote.useCrossOriginEmbedderPolicy", true);
pref("browser.tabs.unloadOnLowMemory", true);
pref("browser.places.speculativeConnect.enabled", true);
pref("browser.urlbar.speculativeConnect.enabled", true);
pref("browser.uitour.enabled", false);
pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons", false);
pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features", false);

// ════════════════════════════════════════════════════════════════════════
//  Telemetry / background services — compile-inert code
// ════════════════════════════════════════════════════════════════════════
pref("toolkit.telemetry.enabled", false);
pref("toolkit.telemetry.unified", false);
pref("toolkit.telemetry.server", "data:,");
pref("toolkit.telemetry.archive.enabled", false);
pref("toolkit.telemetry.newProfilePing.enabled", false);
pref("toolkit.telemetry.shutdownPingSender.enabled", false);
pref("toolkit.telemetry.updatePing.enabled", false);
pref("toolkit.telemetry.bhrPing.enabled", false);
pref("toolkit.telemetry.firstShutdownPing.enabled", false);
pref("toolkit.coverage.enabled", false);
pref("toolkit.coverage.endpoint.base", "");
pref("datareporting.healthreport.uploadEnabled", false);
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("datareporting.usage.uploadEnabled", false);
pref("app.normandy.enabled", false);
pref("app.normandy.api_url", "");
pref("app.shield.optoutstudies.enabled", false);
pref("captchadetection.actor.enabled", false);       // stock true — background service
pref("extensions.webcompat-reporter.enabled", false);
pref("extensions.getAddons.cache.enabled", false);
pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
pref("browser.newtabpage.activity-stream.telemetry", false);
pref("browser.discovery.enabled", false);
pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
pref("breakpad.reportURL", "");
pref("browser.contentblocking.report.lockwise.enabled", false);
pref("browser.contentblocking.report.monitor.enabled", false);
EOF

    # ── A.2 bench block: force-enables, blocklist bypass, Spectre, a11y ─────
    if [[ "$PROFILE" == "bench" ]]; then
        cat >> "$f" <<'EOF'

// ────────────────────────────────────────────────────────────────────────
//  HELLFIRE_PROFILE=bench — NOT in the public build.
//  Blocklist bypass + force-enables (crash/artifact risk on the drivers the
//  blocklist is right about), Spectre + timer precision off (parent-process
//  safety only; no benchmark gain — see the JS section), a11y and spellcheck
//  off. Do not browse hostile content in this build.
// ────────────────────────────────────────────────────────────────────────
pref("gfx.webrender.all", true);
pref("gfx.webrender.compositor.force-enabled", true);
pref("gfx.x11-egl.force-enabled", true);
pref("widget.dmabuf.force-enabled", true);
pref("layers.acceleration.force-enabled", true);
pref("media.hardware-video-decoding.force-enabled", true);
pref("webgl.force-enabled", true);
pref("webgl.msaa-force", true);
pref("webgl.enable-draft-extensions", true);
pref("webgl.disable-fail-if-major-performance-caveat", true);
pref("dom.webgpu.enabled", true);
pref("dom.webgpu.external-texture.enabled", true);   // zero-copy video → WebGPU
pref("gfx.webgpu.ignore-blocklist", true);
pref("javascript.options.spectre.index_masking", false);
pref("javascript.options.spectre.object_mitigations", false);
pref("javascript.options.spectre.string_mitigations", false);
pref("javascript.options.spectre.value_masking", false);
pref("privacy.reduceTimerPrecision", false);         // full-resolution performance.now()
pref("layout.spellcheckDefault", 0);
pref("accessibility.force_disabled", 1);             // disables screen readers
EOF
    fi

    printf '%s\n' "$MARK_END" >> "$f"

    local n
    n=$(sed -n '/HELLFIRE_PATCH_START/,/HELLFIRE_PATCH_END/p' "$f" | grep -c '^pref(' || true)
    ok "  → $n pref defaults installed ($PROFILE profile — run --check-prefs after pulls)"
}

# ────────────────────── B. Graphics blocklist neuter  [bench only] ───────────
apply_gfxinfo() {
    local f="widget/GfxInfo.cpp"
    backup_file "$f" || return 0

    log "B. neutering Linux HW-decode / WebRender blocklists in $f"

    # Wrap every APPEND_TO_DRIVER_BLOCKLIST* block whose text contains one of
    # the markers AND whose status is a block (FEATURE_BLOCKED_* /
    # FEATURE_DISCOURAGED / FEATURE_DENIED) in `#if 0 ... #endif`.
    # FEATURE_ROLLOUT_* / FEATURE_ALLOW_* entries are allow-rules and are
    # left alone — wrapping them turns features OFF.
    python3 - "$f" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()

markers = [
    "FEATURE_HARDWARE_VIDEO_DECODING_NO_LINUX_NVIDIA",
    "FEATURE_HARDWARE_VIDEO_DECODING_MESA",
    "FEATURE_HARDWARE_VIDEO_DECODING_AMD_DISABLE",
    "FEATURE_ROLLOUT_ALL_LINUX",
    "FEATURE_WEBRENDER_DISABLED_NVIDIA_LINUX",
    "FEATURE_WEBRENDER_SOFTWARE",
    "FEATURE_WEBRENDER_NVIDIA_LINUX",
    "FEATURE_HARDWARE_VIDEO_DECODING_TEST",
    "FEATURE_H264_HARDWARE_VIDEO_DECODING_NO_LINUX_NVIDIA",
]
block_statuses = ("FEATURE_BLOCKED", "FEATURE_DISCOURAGED", "FEATURE_DENIED")

# Match a full APPEND_TO_DRIVER_BLOCKLIST*(...); block
pat = re.compile(r'APPEND_TO_DRIVER_BLOCKLIST[A-Z_]*\s*\([^;]*?\);', re.DOTALL)
count = 0
skipped_allow = 0
def repl(m):
    global count, skipped_allow
    body = m.group(0)
    if not any(mk in body for mk in markers):
        return body
    if not any(s in body for s in block_statuses):
        skipped_allow += 1
        return body
    count += 1
    return "#if 0 /* hellfire: neutered */\n" + body + "\n#endif"
src2 = pat.sub(repl, src)
if count == 0:
    print("  (warning) no matching blocklist blocks found — upstream changed layout")
else:
    open(path, "w").write(src2)
    print(f"  → neutered {count} blocklist entr{'y' if count==1 else 'ies'}")
if skipped_allow:
    print(f"  → left {skipped_allow} ALLOW/rollout entr{'y' if skipped_allow==1 else 'ies'} untouched")
PY
}

# ────────────────────── C. mozjemalloc tuning ───────────────────────────────
apply_mozjemalloc() {
    local f="memory/build/mozjemalloc.cpp"
    backup_file "$f" || return 0

    log "C. tuning mozjemalloc (arenas, dirty-page purge threshold)"

    # C.1 Arena count: CPUs → CPUs * 2 (reduces per-arena lock contention)
    if grep -q 'narenas = GetNumberOfProcessors' "$f"; then
        sed -i 's|narenas = GetNumberOfProcessors();|narenas = GetNumberOfProcessors() * 2;|' "$f"
        ok "  → narenas = ncpus * 2"
    elif grep -qE 'narenas\s*=\s*num_cpus' "$f"; then
        sed -i -E 's|narenas\s*=\s*num_cpus;|narenas = num_cpus * 2;|' "$f"
        ok "  → narenas = num_cpus * 2"
    else
        warn "  C.1: arena anchor not found — skipping"
    fi

    # C.2 Dirty-page purge threshold: keep more dirty pages around;
    # fewer madvise/munmap syscalls on alloc-heavy workloads
    if grep -qE 'opt_dirty_max\s*=\s*\(?1U?\s*<<\s*[0-9]+\)?' "$f"; then
        sed -i -E 's|opt_dirty_max\s*=\s*\(?1U?\s*<<\s*[0-9]+\)?;|opt_dirty_max = (1U << 10);|' "$f"
        ok "  → opt_dirty_max = 1024 pages"
    elif grep -qE '#define\s+DIRTY_MAX_DEFAULT' "$f"; then
        sed -i -E 's|#define\s+DIRTY_MAX_DEFAULT\s+.*|#define DIRTY_MAX_DEFAULT (1U << 10)|' "$f"
        ok "  → DIRTY_MAX_DEFAULT = 1024 pages"
    else
        warn "  C.2: dirty-max anchor not found — skipping"
    fi
}

# ────────────────────── D. Ion JIT inlining constants ───────────────────────
apply_ion_inlining() {
    local f="js/src/jit/JitOptions.cpp"
    backup_file "$f" || return 0

    log "D. bumping Ion inlining limits in $f"

    # Only the names that exist on the current tree are rewritten; on
    # Warp-era trees several of the IonBuilder-era ones simply won't match.
    python3 - "$f" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
# Map of (identifier -> new value). These are ctor-initialized fields on
# DefaultJitOptions; we rewrite the RHS of "SET_DEFAULT(name, VAL);" lines.
targets = {
    "smallFunctionMaxBytecodeLength":  "200",   # 130 → 200
    "inlineMaxBytecodePerCallSite":    "10000", # ~3500 → 10000
    "inliningMaxCallerBytecodeLength": "20000", # 10000 → 20000
    "inliningEntryThreshold":          "50",    # 100 → 50
    "inliningWarmUpThresholdFactor":   "0.1",   # 0.125 → 0.1  (inline sooner)
    "trialInliningInitialWarmUpCount": "100",   # 500 → 100
}
changed = 0
for name, val in targets.items():
    pat = re.compile(
        r'(SET_DEFAULT\s*\(\s*' + re.escape(name) + r'\s*,\s*)[^,\)]+(\s*\))'
    )
    src2, n = pat.subn(r'\g<1>' + val + r'\g<2>', src)
    if n:
        src = src2
        changed += n
if changed:
    open(path, "w").write(src)
    print(f"  → updated {changed} Ion inlining default(s)")
else:
    print("  (warning) no Ion inlining defaults matched — upstream refactored")
PY
}

# ────────────── E. retired (Pocket / Normandy DIRS strip) — see changelog ────

# ────────────── F. PGO training-corpus extension ────────────────────────────
# With MOZ_PGO=1, mach runs an instrumented build through
# build/pgo/profileserver.py, which serves the corpus listed in
# build/pgo/index.html. On FF155 that corpus already includes ONE auto-started
# Speedometer 3 pass (served from third_party/webkit/PerformanceTests/
# Speedometer3 on port 8000 with ?startAutomatically=true, extendedTimeout).
# This patch adds a SECOND pass, doubling PGO coverage of the JS-engine /
# Stylo (Rust) / layout hot paths this build is tuned for. Costs a few extra
# minutes in the profile step of the build.
apply_pgo_corpus() {
    local f="build/pgo/index.html"
    if [[ ! -d third_party/webkit/PerformanceTests/Speedometer3 ]]; then
        warn "F. skip: third_party/webkit/PerformanceTests/Speedometer3 not in tree"
        return 0
    fi
    backup_file "$f" || return 0

    log "F. extending PGO training corpus (second Speedometer 3 pass)"

    python3 - "$f" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
if "hellfire-sp3-extra" in src:
    print("  (already present)")
    sys.exit(0)
pat = re.compile(
    r'(new Item\(\s*"http://localhost:8000/index\.html\?startAutomatically=true",\s*extendedTimeout\s*\))'
)
m = pat.search(src)
if not m:
    print("  (warning) SP3 item anchor not found — index.html changed upstream;")
    print("            add another new Item(...) for localhost:8000 manually")
    sys.exit(0)
# superExtendedTimeout is not guaranteed to exist. An undefined identifier
# here throws while the tests array is built and the whole training run
# silently degrades, so fall back to the identifier we know is there.
timeout = ("superExtendedTimeout"
           if re.search(r'\bsuperExtendedTimeout\b', src) else "extendedTimeout")
extra = m.group(1) + (
    ',\n    // hellfire-sp3-extra: second full Speedometer 3 pass = 2x PGO coverage\n'
    '    // of JS-engine / Stylo / layout hot paths in the training run\n'
    '    new Item(\n'
    '      "http://localhost:8000/index.html?startAutomatically=true",\n'
    f'      {timeout}\n'
    '    )'
)
open(path, "w").write(pat.sub(lambda _m: extra, src, count=1))
print(f"  → PGO corpus: Speedometer 3 now runs twice per training run ({timeout})")
PY
}

# ────────────────────── commands ────────────────────────────────────────────
cmd_apply() {
    verify_tree
    case "$PROFILE" in
        public|bench) ;;
        *) err "HELLFIRE_PROFILE must be 'public' or 'bench' (got '$PROFILE')"; exit 2 ;;
    esac
    if [[ -f "$STATE_FILE" ]]; then
        err "Already applied. Run --revert first (or --status to inspect)."
        exit 1
    fi
    if [[ -d "$BACKUP_DIR" ]]; then
        err "$BACKUP_DIR/ exists but $STATE_FILE does not — the state file was removed by"
        err "hand. Inspect/restore the backups, then rm -rf $BACKUP_DIR before applying again."
        exit 1
    fi
    : > "$STATE_FILE"
    mkdir -p "$BACKUP_DIR"

    log "applying HellFire performance patch set v${SCRIPT_VERSION} — profile: ${GRN}${PROFILE}${RST}"
    apply_prefs
    if [[ "$PROFILE" == "bench" ]]; then
        apply_gfxinfo
    else
        log "B. skipped — public profile keeps widget/GfxInfo.cpp's blocklist intact"
    fi
    apply_mozjemalloc
    apply_ion_inlining
    apply_pgo_corpus

    local n
    n=$(wc -l < "$STATE_FILE")
    ok "done — $n file(s) modified. Backups in ${DIM}$BACKUP_DIR/${RST}"
    log "you may now run: ${GRN}./mach build${RST}  (MOZ_PGO=1 in mozconfig → all three PGO stages run by themselves)"
    log "tip: run ${GRN}./hellfire_patcher.sh --check-prefs${RST} after every upstream pull"
}

cmd_revert() {
    verify_tree
    if [[ ! -f "$STATE_FILE" ]] || [[ ! -s "$STATE_FILE" ]]; then
        warn "nothing to revert (no state file)"
        [[ -d "$BACKUP_DIR" ]] && rm -rf "$BACKUP_DIR"
        rm -f "$STATE_FILE"
        return 0
    fi

    log "reverting HellFire patches"
    local n=0
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        local b="$BACKUP_DIR/$f"
        if [[ -f "$b" ]]; then
            cp -p "$b" "$f"
            n=$((n+1))
            printf '  %srestored%s %s\n' "$GRN" "$RST" "$f"
        else
            warn "  missing backup for $f — skipped"
        fi
    done < "$STATE_FILE"

    rm -rf "$BACKUP_DIR"
    rm -f "$STATE_FILE"
    ok "done — $n file(s) restored. Tree is clean for git/hg pull."
}

cmd_status() {
    verify_tree
    if [[ ! -f "$STATE_FILE" ]]; then
        log "status: ${YLW}not applied${RST}"
        return 0
    fi
    local n prof
    n=$(wc -l < "$STATE_FILE")
    prof=$(grep -o 'profile=[a-z]*' browser/app/profile/firefox.js 2>/dev/null | head -n1 | cut -d= -f2 || true)
    log "status: ${GRN}applied${RST} (profile: ${prof:-unknown}) — $n file(s) modified:"
    sed 's/^/  • /' "$STATE_FILE"
}

# Audit every pref name in section A (public + bench blocks) against THIS
# tree. A pref counts as live if its exact name is
#   1. a `name:` field in StaticPrefList.yaml,
#   2. a pref("...") default in all.js or stock firefox.js (our block stripped),
#   3. a "..." string literal anywhere in code (runtime Preferences::Get* /
#      Services.prefs readers).
# Whole-name matching: a dead pref that is a prefix of a live one is reported.
cmd_check_prefs() {
    verify_tree
    local names
    mapfile -t names < <(sed -n 's/^pref("\([^"]*\)".*/\1/p' "$0" | LC_ALL=C sort -u)
    if ((${#names[@]} == 0)); then
        err "no pref() lines found in $0"
        exit 1
    fi
    log "checking ${#names[@]} prefs (public + bench blocks) against the source tree…"

    local pats quoted live dead ff self
    pats=$(mktemp); quoted=$(mktemp); live=$(mktemp); dead=$(mktemp)
    printf '%s\n' "${names[@]}" > "$pats"
    sed 's/.*/"&"/' "$pats" > "$quoted"
    ff=browser/app/profile/firefox.js
    self=$(basename "$0")

    {
        # 1. static pref definitions
        sed -n 's/^- *name: *//p' modules/libpref/init/StaticPrefList.yaml 2>/dev/null || true
        # 2. pref() defaults in all.js + stock firefox.js (our block stripped —
        #    otherwise a post-apply run matches every name against itself)
        {
            cat modules/libpref/init/all.js 2>/dev/null || true
            sed '/HELLFIRE_PATCH_START/,/HELLFIRE_PATCH_END/d' "$ff" 2>/dev/null || true
        } | sed -n 's/^[[:space:]]*pref("\([^"]*\)".*/\1/p'
        # 3. "name" string literals in code (tracked files only under git)
        if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            git grep -hoF -f "$quoted" -- . ":(exclude)$ff" ":(exclude)$self" 2>/dev/null || true
        else
            grep -rhoF -f "$quoted" \
                --exclude-dir=.hellfire_backup --exclude-dir=.git --exclude-dir=.hg \
                --exclude-dir='obj*' --exclude=firefox.js --exclude="$self" \
                --include='*.cpp' --include='*.h' --include='*.mm' --include='*.js' \
                --include='*.jsm' --include='*.mjs' --include='*.rs' --include='*.yaml' \
                . 2>/dev/null || true
        fi | tr -d '"'
    } | LC_ALL=C sort -u > "$live"

    LC_ALL=C comm -23 "$pats" "$live" > "$dead"
    if [[ -s "$dead" ]]; then
        warn "dead / renamed on this tree ($(wc -l < "$dead") pref(s)):"
        sed 's/^/  ✗ /' "$dead"
        warn "remove or update these in section A, then rebuild"
    else
        ok "all ${#names[@]} prefs are defined or referenced in this tree"
    fi
    rm -f "$pats" "$quoted" "$live" "$dead"
}

cmd_help() {
    cat <<EOF
hellfire_patcher.sh v${SCRIPT_VERSION} — Firefox / HellFire perf patches for GNU/Linux

USAGE
  ./hellfire_patcher.sh --apply        apply all patches (before ./mach build)
  ./hellfire_patcher.sh --revert       restore originals (before git/hg pull)
  ./hellfire_patcher.sh --status       show applied state + profile
  ./hellfire_patcher.sh --check-prefs  audit pref names against this tree
  ./hellfire_patcher.sh --help         this screen

PROFILES  (HELLFIRE_PROFILE=public|bench, default public)
  public  the build you package. No Spectre/timer changes, a11y untouched,
          no blocklist bypass or *.force-enabled, GfxInfo.cpp left alone.
  bench   public + force-enables / blocklist bypass, Spectre and timer
          precision off, a11y + spellcheck off, section B. Your box only.

WORKFLOW
  cd mozilla-unified
  ./hellfire_patcher.sh --apply        # or: HELLFIRE_PROFILE=bench ./hellfire_patcher.sh --apply
  ./mach build                         # MOZ_PGO=1 in mozconfig: all three PGO stages run by themselves
  # ... later, to pull upstream changes ...
  ./hellfire_patcher.sh --revert
  git pull        # or: hg pull -u
  ./hellfire_patcher.sh --check-prefs  # catch pref renames/removals early
  ./hellfire_patcher.sh --apply
  ./mach build

PATCHES APPLIED
  A. ~185 (public) / ~205 (bench) runtime pref defaults  (browser/app/profile/firefox.js)
       Audited against mozilla-central FF155. WebRender native compositor +
       shader precache/disk-binary, canvas cache 16384 items / 512 MB, skia
       font cache 80 MB, image cache 256 MB + surface cache cap 4 GB with
       5-min retention, VA-API/AV1/ffvpx HW decode (GPU process NOT forced),
       media cache 2 GB on disk + 128 MB/1 GB in memory + 10-min readahead,
       JIT thresholds 10/10/100 with inline bytecode 200, wasm relaxed SIMD,
       spectre.disable_for_isolated_content pinned true, GC parallel marking
       x8 threads with 10 ms slices and RAM-greedy heap growth, nursery min
       4 MB, 256 MB mem cache + 4 GB disk cache + uncompressed JS bytecode
       cache, HTTP/3 + 0-RTT + 8 MB QUIC recv buffer, happy eyeballs, H2
       concurrent 200, keep-alive 300 s, DNS prefetch everywhere + 4000-entry
       10-min DNS cache, prefetch-next + hover preconnect + early hints,
       ssl-token cache 10240, parser yield 250 ms with initialpaint 5 ms,
       background tabs throttled to 1 fps, APZ overscroll + paint-skipping,
       8+8 content procs with prelaunch + forkserver + tab warmup, fission
       autostart, speculative connect (places + urlbar), telemetry / Normandy
       / CFR / captchadetect / crashreport / coverage kill.
       bench adds: gfx.webrender.all + every *.force-enabled, WebGL force +
       MSAA + draft extensions, WebGPU + blocklist bypass + external texture,
       Spectre mitigations off in all processes, full timer precision,
       spellcheck off, a11y force_disabled.
  B. HW-decode / WebRender blocklist neuter  (widget/GfxInfo.cpp)   [bench only]
       Wraps NVIDIA + Mesa + non-Mesa AMD *block* entries in #if 0; leaves
       FEATURE_ROLLOUT_* / *_ALLOW_* entries alone.
  C. mozjemalloc tuning              (memory/build/mozjemalloc.cpp)
       narenas = ncpus x 2  +  opt_dirty_max bumped to 1024 pages
       (fewer madvise/munmap syscalls on alloc-heavy workloads). Skips
       cleanly when the anchors are gone.
  D. Ion inlining limits             (js/src/jit/JitOptions.cpp)
       smallFunctionMaxBytecodeLength 130→200, trialInliningInitialWarmUpCount
       →100 and friends, whichever still exist on the tree.
  E. retired in v2.2 — the Normandy DIRS strip could dangle
       resource://normandy/ imports and break moz.build; the prefs already
       make Normandy inert. Pocket is gone from the tree.
  F. PGO training-corpus extension   (build/pgo/index.html)
       Adds a second auto-started Speedometer 3 pass to the profileserver
       corpus (superExtendedTimeout if the tree defines it, else
       extendedTimeout). Doubles JS/Stylo/layout hot-path coverage at the
       cost of a few extra minutes per PGO build. Skipped cleanly if
       Speedometer3 is absent from the tree.

NOTES
  * --apply refuses to run if already applied or if a stale .hellfire_backup/
    is lying around; --revert is idempotent.
  * Backups live in .hellfire_backup/ — do not delete between apply/revert.
    Add .hellfire_backup/ and .hellfire_applied to .git/info/exclude.
  * --check-prefs works applied or not; run it after every pull. It verifies
    that names exist, NOT that stock values are still what the comments say.
  * The PGO profile run launches the instrumented browser and needs a
    display: run ./mach build inside your session or under xvfb-run.
  * Section F only pays off with MOZ_PGO=1 in mozconfig; without PGO it is
    an inert one-line change to a file nothing else consumes.
  * bench builds: if someone needs a screen reader on one, set
    accessibility.force_disabled to 0 in about:config; if it will ever see
    hostile content, delete the spectre / reduceTimerPrecision lines.
  * dom.ipc.processCount.webIsolated=8 and prelaunch=3 are the remaining
    RAM-hungry public defaults; drop to 4/2 if the target audience includes
    8 GB laptops.
EOF
}

# ────────────────────── entry ───────────────────────────────────────────────
case "${1:-}" in
    --apply|-a)        cmd_apply ;;
    --revert|-r)       cmd_revert ;;
    --status|-s)       cmd_status ;;
    --check-prefs|-c)  cmd_check_prefs ;;
    --help|-h|"")      cmd_help ;;
    *) err "unknown option: $1"; echo; cmd_help; exit 2 ;;
esac
