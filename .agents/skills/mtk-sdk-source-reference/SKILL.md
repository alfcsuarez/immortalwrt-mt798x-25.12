---
name: mtk-sdk-source-reference
description: Use when comparing, importing or validating MTK SDK archives and firmware provenance in this repository's dl directory. Reads pinned offline caches without executing or extracting their contents and distinguishes reference-only sources from active firmware build inputs.
---

# MTK source cache and provenance

Read [the source-cache inventory](../../../package/mtk/pdf/source-cache.json),
[the dl explanation](../../../dl/README.mtk-reference.md) and the current package
Makefiles before proposing archive or driver changes.

## Verify and inspect

Run from the repository root:

```sh
python3 scripts/mtk-sdk-reference.py verify
python3 scripts/mtk-sdk-reference.py archive-list mt799x_20250613-415824.tar.xz --match pp_cmd
python3 scripts/mtk-sdk-reference.py archive-search mt799x_20250613-415824.tar.xz UniCmdPPCapCtrl
python3 scripts/mtk-sdk-reference.py archive-search wappd-24f7e6.tar.bz2 wireless
```

Use `archive-show ARCHIVE MEMBER --start N --lines N` for a bounded source view.
The helper checks the archive digest, reads regular members and refuses binary
text views. It never extracts files or runs an archived program. Content shown
from a tarball is base source; apply the consuming package's patches before
asserting the final implementation behaves that way.

## Interpret the inventory correctly

- `already-present`: the pinned upstream archive matches a previously tracked
  local file. Presence alone does not prove the active package uses it.
- `reference-only`: imported for offline code/ABI/document comparison; no new
  runtime package, default config or init service selects it in this change.
- `not-imported`: an upstream archive was deliberately excluded. The 20250613
  fallback binary package does not supply a verified newer BE14 board firmware.
- `preserved_build_inputs`: existing R4 source/bin and datconf revision whose
  identities were retained; compare these with actual Makefile references.

The Wi-Fi SDK and warp source archives also contain some non-source members.
Preserve each original archive's notices; do not describe all members as source
or assign the repository's code license to third-party PDFs/firmware.

## Compare the implementation, not just archive or package dates

1. Resolve PKG_SOURCE/revision, binary archive selection, custom board firmware
   overrides, patches, shared/split build directories and generated headers.
2. Check file size, SHA-256 and pinned upstream Git blob identity. Use immutable
   URLs for imports; if an input changes, update its manifest evidence.
3. For firmware, compare actual installed board/SKU files and WM/WA/PATCH build
   identifiers. A newer fallback archive name can still install the same or an
   older board file after overrides.
4. Read diff and callers after all patches. File presence and patch titles are
   insufficient: later baseline patches can undo an earlier fix.
5. Keep useful source fixes separate from framework replacement, new Mesh
   services, calibration changes and firmware upgrades. Choose validation based
   on the final authorized change.

The 1905daemon/mapd/wappd/libmapd/libwpactrl/mapfilter caches can be used to check
Multi-AP chapter claims. They do not establish a complete buildable/working Mesh
stack on the current WEXT firmware. Check application/driver ABI, hostapd mode,
UCI ownership, roles, bridge/VLAN/HNAT interactions and runtime persistence.

## Complete a reference import

For a documentation/cache task, preserve active package selectors and add the
new files, provenance, human analysis and topic routing together. Verify all
hashes and physical pages, exercise the reader, and review the staged diff for
unexpected runtime/configuration files. Commit/publish according to the user's
authorized workflow; do not demand confirmation solely because a reference
document contains lab commands. Do not execute those commands as part of a cache
import.
