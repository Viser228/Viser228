# MT7601U driver experiment — POCO X6 Pro / duchamp

This repository holds a temporary, **experimental** GitHub Actions workflow.

Goal: compile `mt7601u.ko` for Android GKI 6.1, inspect its metadata, and compare it against the device's existing wireless-driver ABI.

- Hardware: USB `148f:7601` (MediaTek MT7601U)
- Target: `6.1.177-GKID-r652` (running kernel)
- Built from a historical source snapshot close to the relevant GKID release; *not guaranteed to be the identical patched kernel source.*
- No phone files, accounts, logs, MAC addresses, or serial numbers are uploaded.

**DO NOT FLASH OR INSMOD THE OUTPUT.** Compilation alone is not a proof of ABI or CFI compatibility. A prior Realtek test caused a kernel crash with mismatched cfg80211/mac80211 modules.

The workflow uses read-only repository permissions and uploads the compiled research result only to short-lived GitHub Actions artifacts.
