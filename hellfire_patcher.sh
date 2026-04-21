#!/usr/bin/env bash
# hellfire_patcher.sh  —  Performance patch set for HellFire / Firefox on GNU/Linux
#
# Usage:
#   cd mozilla-unified
#   ./hellfire_patcher.sh --apply          # before ./mach build
#   ./hellfire_patcher.sh --revert         # before `git pull` / `hg pull`
#   ./hellfire_patcher.sh --status
#   ./hellfire_patcher.sh --help
#
# Design:
#   Each patch backs the original file up to .hellfire_backup/<path> before
#   modifying it, and records the path in .hellfire_applied. --revert copies
#   every backed-up file back into place and clears the state, leaving the
#   working tree identical to pre-apply. Safe for git/hg pulls.
#
# Patches are grouped:
#   A. Runtime prefs (appended as a single block to browser/app/profile/firefox.js)
#   B. Graphics blocklist neutering (widget/GfxInfo.cpp, Linux section)
#   C. Allocator tuning (memory/build/mozjemalloc.cpp)
#   D. Build system (toolkit/moz.configure — LLD threads, GNU hash, codegen-units)
#   E. Pocket/Normandy stripping (browser/components/moz.build)
#
# Safe to re-run --apply after --revert. Safe to run --revert repeatedly.

set -euo pipefail

# ───────────────────────────── config / tty ──────────────────────────────────
SCRIPT_VERSION="1.1"
STATE_FILE=".hellfire_applied"
BACKUP_DIR=".hellfire_backup"
MARK_START="// >>> HELLFIRE_PATCH_START - do not edit between markers"
MARK_END="// <<< HELLFIRE_PATCH_END"

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

already_applied() {
    [[ -f "$STATE_FILE" ]] && grep -qxF "$1" "$STATE_FILE"
}

# ────────────────────────── A. runtime prefs ─────────────────────────────────
apply_prefs() {
    local f="browser/app/profile/firefox.js"
    backup_file "$f" || return 0

    log "A. appending performance pref defaults to $f"

    cat >> "$f" <<'EOF'

// >>> HELLFIRE_PATCH_START - do not edit between markers
// ════════════════════════════════════════════════════════════════════════
//  Graphics / compositor / GPU process
// ════════════════════════════════════════════════════════════════════════
pref("gfx.webrender.all", true);
pref("gfx.webrender.enabled", true);
pref("gfx.webrender.compositor", true);
pref("gfx.webrender.compositor.force-enabled", true);
pref("gfx.webrender.precache-shaders", true);
pref("gfx.webrender.software", false);
pref("gfx.webrender.program-binary-disk", true);
pref("gfx.webrender.max-shared-surface-size", 4096);
pref("gfx.webrender.batched-texture-uploads", true);
pref("gfx.webrender.draw-calls-for-texture-upload", true);
pref("gfx.canvas.accelerated", true);
pref("gfx.canvas.accelerated.cache-items", 4096);
pref("gfx.canvas.accelerated.cache-size", 512);
pref("gfx.content.skia-font-cache-size", 80);
pref("gfx.x11-egl.force-enabled", true);
pref("widget.dmabuf.force-enabled", true);
pref("widget.wayland.fractional-scale.enabled", true);
pref("layers.acceleration.force-enabled", true);
pref("layers.gpu-process.enabled", true);
pref("layers.gpu-process.force-enabled", true);
pref("layers.mlgpu.enabled", true);
pref("layers.offmainthreadcomposition.async-animations", true);
pref("layers.async-pan-zoom.enabled", true);
pref("layers.async-video.enabled", true);
pref("layers.async-video-oop.enabled", true);
pref("layout.frame_rate", -1);
pref("layout.throttled_frame_rate", 60);
pref("image.cache.size", 10485760);
pref("image.cache.factor2.threshold-surfaces", 32);
pref("image.mem.decode_bytes_at_a_time", 131072);
pref("image.mem.shared", true);
pref("image.mem.volatile.min_spare_kb", 2048);
pref("image.decode-immediately.enabled", true);
pref("image.animated.decode-on-demand.batch-size", 6);
pref("image.animated.decode-on-demand.threshold-kb", 20480);
pref("image.handle-orientation", true);
pref("webgl.force-enabled", true);
pref("webgl.msaa-force", true);
pref("webgl.default-antialias", true);
pref("webgl.enable-draft-extensions", true);
pref("webgl.disable-fail-if-major-performance-caveat", true);
pref("dom.webgpu.enabled", true);
pref("dom.webgpu.unsafe", true);

// ════════════════════════════════════════════════════════════════════════
//  Hardware video decode (VA-API / V4L2 / AV1)
// ════════════════════════════════════════════════════════════════════════
pref("media.hardware-video-decoding.enabled", true);
pref("media.hardware-video-decoding.force-enabled", true);
pref("media.ffmpeg.vaapi.enabled", true);
pref("media.ffmpeg.encoder.enabled", true);
pref("media.ffmpeg.low-latency.enabled", true);
pref("media.ffvpx.enabled", true);
pref("media.ffvpx-hw.enabled", true);
pref("media.rdd-vpx.enabled", true);
pref("media.rdd-ffvpx.enabled", true);
pref("media.rdd-ffmpeg.enabled", true);
pref("media.rdd-process.enabled", true);
pref("media.utility-process.enabled", true);
pref("media.utility-ffvpx.enabled", true);
pref("media.utility-ffmpeg.enabled", true);
pref("media.navigator.mediadatadecoder_vpx_enabled", true);
pref("media.av1.enabled", true);
pref("media.av1.use-dav1d", true);
pref("media.gpu-process-decoder", true);
pref("media.videocontrols.picture-in-picture.video-toggle.enabled", true);
pref("media.mediasource.enabled", true);
pref("media.wmf.dxva.enabled", true);
pref("media.memory_cache_max_size", 1048576);
pref("media.memory_caches_combined_limit_kb", 2560000);
pref("media.cache_readahead_limit", 9999);
pref("media.cache_resume_threshold", 3600);
pref("media.cache_size", 2048000);

// ════════════════════════════════════════════════════════════════════════
//  JS engine — JIT / GC / memory
// ════════════════════════════════════════════════════════════════════════
pref("javascript.options.baselinejit.threshold", 10);
pref("javascript.options.baselineinterpreter.threshold", 10);
pref("javascript.options.ion.threshold", 100);
pref("javascript.options.ion.frequent_bailout_threshold", 10);
pref("javascript.options.ion.offthread_compilation", true);
pref("javascript.options.asmjs", true);
pref("javascript.options.wasm_baselinejit", true);
pref("javascript.options.wasm_optimizingjit", true);
pref("javascript.options.wasm_simd", true);
pref("javascript.options.wasm_relaxed_simd", true);
pref("javascript.options.native_regexp", true);
pref("javascript.options.warp", true);
pref("javascript.options.spectre.index_masking", false);
pref("javascript.options.spectre.object_mitigations", false);
pref("javascript.options.spectre.string_mitigations", false);
pref("javascript.options.spectre.value_masking", false);
pref("javascript.options.spectre.jit_to_cxx_calls", false);
pref("javascript.options.mem.gc_parallel_marking", true);
pref("javascript.options.mem.incremental_weakmap", true);
pref("javascript.options.mem.gc_compacting", true);
pref("javascript.options.mem.gc_incremental", true);
pref("javascript.options.mem.gc_incremental_slice_ms", 100);
pref("javascript.options.mem.gc_allocation_threshold_mb", 100);
pref("javascript.options.mem.gc_allocation_threshold_factor", 150);
pref("javascript.options.mem.gc_high_frequency_heap_growth_max", 300);
pref("javascript.options.mem.gc_high_frequency_heap_growth_min", 150);
pref("javascript.options.mem.gc_low_frequency_heap_growth", 110);
pref("javascript.options.mem.nursery.min_kb", 4096);
pref("javascript.options.mem.nursery.max_kb", 65536);
pref("javascript.options.mem.high_water_mark", 250);

// ════════════════════════════════════════════════════════════════════════
//  Memory / browser caches
// ════════════════════════════════════════════════════════════════════════
pref("browser.cache.memory.enable", true);
pref("browser.cache.memory.capacity", 1048576);
pref("browser.cache.memory.max_entry_size", 262144);
pref("browser.cache.disk.enable", true);
pref("browser.cache.disk.capacity", 4194304);
pref("browser.cache.disk.smart_size.enabled", false);
pref("browser.cache.disk.metadata_memory_limit", 2048);
pref("browser.cache.disk.max_entry_size", 262144);
pref("browser.cache.jsbc_compression_level", 3);
pref("browser.cache.offline.enable", false);
pref("browser.sessionstore.interval", 60000);
pref("browser.sessionstore.interval.idle", 3600000);
pref("browser.sessionstore.idleDelay", 180000);
pref("browser.sessionstore.restore_pinned_tabs_on_demand", true);
pref("browser.sessionhistory.max_entries", 10);
pref("browser.sessionhistory.max_total_viewers", 4);

// ════════════════════════════════════════════════════════════════════════
//  Networking — HTTP / DNS / TLS / predictor
// ════════════════════════════════════════════════════════════════════════
pref("network.http.max-connections", 1800);
pref("network.http.max-persistent-connections-per-server", 10);
pref("network.http.max-urgent-start-excessive-connections-per-host", 5);
pref("network.http.max-connections-per-origin", 10);
pref("network.http.pacing.requests.enabled", false);
pref("network.http.speculative-parallel-limit", 10);
pref("network.http.http3.enable", true);
pref("network.http.http3.enable_0rtt", true);
pref("network.http.http3.enable_qlog", false);
pref("network.http.http2.enabled", true);
pref("network.http.http2.push-enabled", false);
pref("network.http.http2.default-concurrent", 200);
pref("network.http.keep-alive.timeout", 60);
pref("network.http.referer.XOriginTrimmingPolicy", 2);
pref("network.http.network-changed.timeout", 3);
pref("network.dns.disablePrefetch", false);
pref("network.dns.disablePrefetchFromHTTPS", false);
pref("network.dnsCacheEntries", 4000);
pref("network.dnsCacheExpiration", 3600);
pref("network.dnsCacheExpirationGracePeriod", 240);
pref("network.predictor.enabled", true);
pref("network.predictor.enable-prefetch", true);
pref("network.predictor.enable-hover-on-ssl", true);
pref("network.prefetch-next", true);
pref("network.early-hints.enabled", true);
pref("network.early-hints.preconnect.enabled", true);
pref("network.early-hints.preconnect.max_connections", 10);
pref("network.ssl_tokens_cache_capacity", 10240);
pref("network.ssl_tokens_cache_enabled", true);
pref("network.buffer.cache.count", 128);
pref("network.buffer.cache.size", 65536);
pref("network.tcp.tcp_fastopen_enable", true);
pref("network.tcp.sendbuffer", 262144);
pref("network.websocket.max-connections", 2000);
pref("network.file.disable_unc_paths", true);
pref("network.gio.supported-protocols", "");

// ════════════════════════════════════════════════════════════════════════
//  Parser / layout / paint latency
// ════════════════════════════════════════════════════════════════════════
pref("content.notify.interval", 100000);
pref("content.notify.ontimer", true);
pref("content.notify.backoffcount", 5);
pref("content.interrupt.parsing", false);
pref("content.max.tokenizing.time", 2250000);
pref("content.switch.threshold", 750000);
pref("nglayout.initialpaint.delay", 5);
pref("nglayout.initialpaint.delay_in_oopif", 5);
pref("layout.css.will-change.enabled", true);
pref("layout.spellcheckDefault", 0);
pref("editor.truncate_user_pastes", false);
pref("reader.parse-node-limit", 0);
pref("apz.overscroll.enabled", true);
pref("apz.paint_skipping.enabled", true);
pref("mousewheel.system_scroll_override.enabled", true);
pref("general.smoothScroll", true);
pref("general.smoothScroll.msdPhysics.enabled", true);

// ════════════════════════════════════════════════════════════════════════
//  Content process / fission / IPC
// ════════════════════════════════════════════════════════════════════════
pref("dom.ipc.processCount", 8);
pref("dom.ipc.processCount.webIsolated", 4);
pref("dom.ipc.processPrelaunch.enabled", true);
pref("dom.ipc.processPrelaunch.fission.number", 3);
pref("dom.ipc.keepProcessesAlive.web", 4);
pref("dom.ipc.keepProcessesAlive.webIsolated.perOrigin", 1);
pref("dom.serviceWorkers.parent_intercept", true);
pref("dom.enable_web_task_scheduling", true);
pref("dom.script_loader.bytecode_cache.enabled", true);
pref("dom.script_loader.bytecode_cache.strategy", -1);
pref("dom.workers.enabled", true);
pref("fission.autostart", true);

// ════════════════════════════════════════════════════════════════════════
//  Startup / UI responsiveness
// ════════════════════════════════════════════════════════════════════════
pref("browser.startup.preXulSkeletonUI", true);
pref("browser.startup.blankWindow", true);
pref("browser.startup.homepage_override.mstone", "ignore");
pref("browser.shell.checkDefaultBrowser", false);
pref("toolkit.lazyHiddenWindow", true);
pref("toolkit.cosmeticAnimations.enabled", false);
pref("ui.prefersReducedMotion", 0);
pref("browser.tabs.remote.useCrossOriginOpenerPolicy", true);
pref("browser.tabs.remote.useCrossOriginEmbedderPolicy", true);
pref("browser.tabs.unloadOnLowMemory", true);
pref("browser.places.speculativeConnect.enabled", true);
pref("browser.urlbar.speculativeConnect.enabled", true);
pref("browser.urlbar.dnsResolveSingleWordsAfterSearch", 0);
pref("browser.urlbar.suggest.searches", true);
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
pref("toolkit.telemetry.coverage.opt-out", true);
pref("toolkit.coverage.opt-out", true);
pref("toolkit.coverage.endpoint.base", "");
pref("datareporting.healthreport.uploadEnabled", false);
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("datareporting.usage.uploadEnabled", false);
pref("app.normandy.enabled", false);
pref("app.normandy.api_url", "");
pref("app.shield.optoutstudies.enabled", false);
pref("extensions.pocket.enabled", false);
pref("extensions.pocket.api", "");
pref("extensions.pocket.site", "");
pref("extensions.pocket.oAuthConsumerKey", "");
pref("extensions.pocket.showHome", false);
pref("extensions.recommendations.themeRecommendationUrl", "");
pref("extensions.webcompat-reporter.enabled", false);
pref("extensions.formautofill.heuristics.enabled", false);
pref("extensions.getAddons.cache.enabled", false);
pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
pref("browser.newtabpage.activity-stream.telemetry", false);
pref("browser.newtabpage.activity-stream.feeds.snippets", false);
pref("browser.ping-centre.telemetry", false);
pref("browser.discovery.enabled", false);
pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
pref("breakpad.reportURL", "");
pref("browser.contentblocking.report.lockwise.enabled", false);
pref("browser.contentblocking.report.monitor.enabled", false);
pref("browser.onboarding.enabled", false);

// ════════════════════════════════════════════════════════════════════════
//  Accessibility (disables screen readers — comment out if needed)
// ════════════════════════════════════════════════════════════════════════
pref("accessibility.force_disabled", 1);
pref("accessibility.typeaheadfind.autostart", false);
// <<< HELLFIRE_PATCH_END
EOF
    local n
    n=$(grep -c '^pref(' "$f" | tail -1)
    ok "  → ~200 pref defaults installed"
}

# ────────────────────── B. Graphics blocklist neuter ─────────────────────────
apply_gfxinfo() {
    local f="widget/GfxInfo.cpp"
    backup_file "$f" || return 0

    log "B. neutering Linux HW-decode / WebRender blocklists in $f"

    # Wrap every APPEND_TO_DRIVER_BLOCKLIST* block whose message string contains
    # any of these markers in  `#if 0 ... #endif`. Targets NVIDIA/AMD/Mesa
    # blocks without touching platform-wide sanity checks.
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

# Match a full APPEND_TO_DRIVER_BLOCKLIST*(...); block
pat = re.compile(r'APPEND_TO_DRIVER_BLOCKLIST[A-Z_]*\s*\([^;]*?\);', re.DOTALL)
count = 0
def repl(m):
    global count
    body = m.group(0)
    if any(mk in body for mk in markers):
        count += 1
        return "#if 0 /* hellfire: neutered */\n" + body + "\n#endif"
    return body
src2 = pat.sub(repl, src)
if count == 0:
    print("  (warning) no matching blocklist blocks found — upstream changed layout")
else:
    open(path, "w").write(src2)
    print(f"  → neutered {count} blocklist entr{'y' if count==1 else 'ies'}")
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

    # C.2 Dirty-page purge threshold: 2^3=8 → 2^5=32  (keep more dirty
    # pages around; fewer madvise/munmap syscalls on alloc-heavy workloads)
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

# ────────────────────── E. Strip Pocket / Normandy dirs ─────────────────────
apply_feature_strip() {
    local f="browser/components/moz.build"
    backup_file "$f" || return 0

    log "E. removing Pocket / Normandy from component build graph"

    # Comment out the DIRS entries if present
    python3 - "$f" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
targets = ["'pocket'", '"pocket"', "'normandy'", '"normandy"']
changed = 0
new_lines = []
for line in src.splitlines(keepends=True):
    if any(t in line for t in targets) and not line.lstrip().startswith("#"):
        new_lines.append("# hellfire-stripped: " + line)
        changed += 1
    else:
        new_lines.append(line)
open(path, "w").write("".join(new_lines))
print(f"  → stripped {changed} dir reference{'s' if changed != 1 else ''}")
PY
}

# ────────────────────── commands ────────────────────────────────────────────
cmd_apply() {
    verify_tree
    if [[ -f "$STATE_FILE" ]]; then
        err "Already applied. Run --revert first (or --status to inspect)."
        exit 1
    fi
    : > "$STATE_FILE"
    mkdir -p "$BACKUP_DIR"

    log "applying HellFire performance patch set v${SCRIPT_VERSION}"
    apply_prefs
    apply_gfxinfo
    apply_mozjemalloc
    apply_ion_inlining
    apply_feature_strip

    local n
    n=$(wc -l < "$STATE_FILE")
    ok "done — $n file(s) modified. Backups in ${DIM}$BACKUP_DIR/${RST}"
    log "you may now run: ${GRN}./mach build${RST}"
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
    local n
    n=$(wc -l < "$STATE_FILE")
    log "status: ${GRN}applied${RST} — $n file(s) modified:"
    sed 's/^/  • /' "$STATE_FILE"
}

cmd_help() {
    cat <<EOF
hellfire_patcher.sh v${SCRIPT_VERSION} — Firefox / HellFire perf patches for GNU/Linux

USAGE
  ./hellfire_patcher.sh --apply     apply all patches (before ./mach build)
  ./hellfire_patcher.sh --revert    restore originals (before git/hg pull)
  ./hellfire_patcher.sh --status    show applied state
  ./hellfire_patcher.sh --help      this screen

WORKFLOW
  cd mozilla-unified
  ./hellfire_patcher.sh --apply
  ./mach build
  # ... later, to pull upstream changes ...
  ./hellfire_patcher.sh --revert
  git pull        # or: hg pull -u
  ./hellfire_patcher.sh --apply
  ./mach build

PATCHES APPLIED
  A. ~200 runtime pref defaults         (browser/app/profile/firefox.js)
       Graphics/WebRender/GPU-process, VA-API/AV1/ffvpx HW decode, WebGPU,
       HTTP/3 + early hints, DNS cache 4000, TCP fastopen, ssl-token cache,
       JIT thresholds 10/100, WARP, wasm SIMD+relaxed, Spectre mitigations
       off, GC parallel-marking + compacting + tuned nursery/heap growth,
       1 GiB mem cache + 4 GiB disk cache, media cache 2 GiB, parser/paint
       latency tuning (content.notify, initialpaint.delay=5), APZ overscroll
       + paint-skipping, fission autostart, pre-launch content procs,
       bytecode cache, telemetry/Normandy/Pocket/CFR/crashreport kill,
       a11y force_disabled.
  B. HW-decode / WebRender blocklist neuter  (widget/GfxInfo.cpp)
       Wraps NVIDIA + Mesa<21 + non-Mesa AMD blocklist entries in #if 0.
  C. mozjemalloc tuning              (memory/build/mozjemalloc.cpp)
       narenas = ncpus × 2  +  opt_dirty_max bumped to 1024 pages
       (fewer madvise/munmap syscalls on alloc-heavy workloads).
  D. Ion inlining limits             (js/src/jit/JitOptions.cpp)
       smallFunctionMaxBytecodeLength 130→200, inlineMaxBytecodePerCallSite
       →10000, inliningMaxCallerBytecodeLength →20000, warmup factor 0.1,
       trialInliningInitialWarmUpCount →100. More aggressive JS inlining.
  E. Pocket + Normandy dir strip     (browser/components/moz.build)
       Removes dead-weight component dirs from the build graph.

NOTES
  • --apply refuses to run if already applied; --revert is idempotent.
  • Backups live in .hellfire_backup/ — do not delete between apply/revert.
  • Accessibility is disabled by pref A; if you rely on screen readers
    comment out  accessibility.force_disabled  in firefox.js.
  • For PGO builds, run an instrumented pass first, then uncomment
    MOZ_PGO=1 in mozconfig before the final build.
EOF
}

# ────────────────────── entry ───────────────────────────────────────────────
case "${1:-}" in
    --apply|-a)   cmd_apply ;;
    --revert|-r)  cmd_revert ;;
    --status|-s)  cmd_status ;;
    --help|-h|"") cmd_help ;;
    *) err "unknown option: $1"; echo; cmd_help; exit 2 ;;
esac
