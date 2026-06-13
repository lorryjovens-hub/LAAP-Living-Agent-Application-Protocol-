#!/usr/bin/env python3
"""
LAAP Version Sync Tool — 自动同步版本号到所有硬编码位置

用法:
  python laap-sync-version.py              → 显示当前版本差异
  python laap-sync-version.py 5.0.0        → 强制设为指定版本
  python laap-sync-version.py --apply      → 从 VERSION.json 同步
  python laap-sync-version.py --check      → 仅检测差异，不修改

原理: 以 laap_brain/__init__.py 的 LAAP_VERSION 为唯一真理源
"""
import os, sys, re, json
from typing import List, Tuple, Optional

ROOT = r"D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP"
LAAP_BRAIN_INIT = os.path.join(ROOT, "laap_brain", "__init__.py")
VERSION_JSON = os.path.join(ROOT, "VERSION.json")
BRIDGE_AGENT = os.path.join(ROOT, "laap_bridge_agent.py")
AGI_BRIDGE = os.path.join(ROOT, "laap_brain", "agi_bridge.py")
V5_UPGRADE = os.path.join(r"D:\LAAP", "laap", "agi", "v5_upgrade.py")
SOUL_MD = os.path.expanduser("~/AppData/Local/hermes/profiles/laap-avatar/SOUL.md")

# ═══════════════════════════════════════════════════════════════
# 扫描所有硬编码版本号
# ═══════════════════════════════════════════════════════════════

SCAN_PATTERNS: List[Tuple[str, str, str, str]] = [
    # (file, description, regex_pattern, expected_source)
    (LAAP_BRAIN_INIT, "laap_brain __init__", r'LAAP_VERSION\s*=\s*"([^"]+)"', "source"),
    (AGI_BRIDGE, "agi_bridge.get_version()", r'return\s+"([^"]+)"\s+if self\._agent', LAAP_BRAIN_INIT),
    (BRIDGE_AGENT, "bridge default version", r'self\.version\s*=\s*"([^"]+)"', LAAP_BRAIN_INIT),
    (VERSION_JSON, "VERSION.json framework", r'"version":\s*"([^"]+)"', LAAP_BRAIN_INIT),
    (VERSION_JSON, "VERSION.json brain_kernel", r'"laap_brain_kernel":\s*"([^"]+)"', LAAP_BRAIN_INIT),
    (VERSION_JSON, "VERSION.json v5 engine", r'"v5_upgrade_engine":\s*"([^"]+)"', LAAP_BRAIN_INIT),
    (VERSION_JSON, "VERSION.json bridge", r'"hermes_bridge":\s*"([^"]+)"', LAAP_BRAIN_INIT),
]


def read_version_from_source() -> Optional[str]:
    """Read the authoritative version from laap_brain/__init__.py"""
    if not os.path.isfile(LAAP_BRAIN_INIT):
        return None
    with open(LAAP_BRAIN_INIT) as f:
        content = f.read()
    m = re.search(r'LAAP_VERSION\s*=\s*"([^"]+)"', content)
    return m.group(1) if m else None


def read_version_from_json() -> Optional[str]:
    if not os.path.isfile(VERSION_JSON):
        return None
    try:
        with open(VERSION_JSON) as f:
            data = json.load(f)
        return data.get("version")
    except Exception:
        return None


def scan_all_versions() -> List[Tuple[str, str, str, str]]:
    """
    Scan all files for version strings.
    Returns list of (file, field, current_version, status)
    """
    source_ver = read_version_from_source()
    results = []

    # Check source
    if source_ver:
        results.append((LAAP_BRAIN_INIT, "LAAP_VERSION (source)", source_ver, "source"))

    # Check agi_bridge
    if os.path.isfile(AGI_BRIDGE):
        with open(AGI_BRIDGE) as f:
            content = f.read()
        m = re.search(r'return\s+"([^"]+)"\s+if self\._agent', content)
        if m:
            status = "✓" if m.group(1) == source_ver else "✗"
            results.append((AGI_BRIDGE, "agi_bridge.get_version()", m.group(1), status))

    # Check bridge_agent
    if os.path.isfile(BRIDGE_AGENT):
        with open(BRIDGE_AGENT) as f:
            content = f.read()
        m = re.search(r'self\.version\s*=\s*"([^"]+)"', content)
        if m:
            status = "✓" if m.group(1) == source_ver else "✗"
            results.append((BRIDGE_AGENT, "bridge default version", m.group(1), status))

    # Check VERSION.json
    json_ver = read_version_from_json()
    if json_ver:
        status = "✓" if json_ver == source_ver else "✗"
        results.append((VERSION_JSON, "framework version", json_ver, status))

    # Check v5_upgrade
    if os.path.isfile(V5_UPGRADE):
        with open(V5_UPGRADE) as f:
            content = f.read()
        m = re.search(r'V5_VERSION\s*=\s*"([^"]+)"', content)
        if m:
            status = "✓" if m.group(1) == source_ver else "✗"
            results.append((V5_UPGRADE, "v5_upgrade.V5_VERSION", m.group(1), status))

    # Check SOUL.md for version references
    if os.path.isfile(SOUL_MD):
        with open(SOUL_MD) as f:
            content = f.read()
        # Find all version-like strings
        versions = re.findall(r'v(\d+\.\d+\.\d+)', content)
        unique = list(set(versions))
        if unique:
            for v in unique:
                status = "✓" if v == source_ver else "✗"
                results.append((SOUL_MD, f"version ref: {v}", v, status))

    return results


def sync_all(target_version: Optional[str] = None, dry_run: bool = False) -> List[str]:
    """Sync all version strings. Returns list of changes made."""
    source_ver = target_version or read_version_from_source()
    if not source_ver:
        return ["ERROR: No source version found"]

    changes = []
    version_json_data = None

    # 1. agi_bridge.py
    if os.path.isfile(AGI_BRIDGE):
        with open(AGI_BRIDGE) as f:
            content = f.read()
        new_content = re.sub(
            r'(return\s+)"[^"]+"(\s+if self\._agent)',
            rf'\1"{source_ver}"\2',
            content
        )
        if new_content != content:
            if not dry_run:
                with open(AGI_BRIDGE, 'w') as f:
                    f.write(new_content)
            changes.append(f"[{'dry:' if dry_run else ''}✓] agi_bridge.py → {source_ver}")

    # 2. bridge_agent.py
    if os.path.isfile(BRIDGE_AGENT):
        with open(BRIDGE_AGENT) as f:
            content = f.read()
        new_content = re.sub(
            r'(self\.version\s*=\s*)"[^"]+"',
            rf'\1"{source_ver}"',
            content
        )
        if new_content != content:
            if not dry_run:
                with open(BRIDGE_AGENT, 'w') as f:
                    f.write(new_content)
            changes.append(f"[{'dry:' if dry_run else ''}✓] laap_bridge_agent.py → {source_ver}")

    # 3. VERSION.json
    if os.path.isfile(VERSION_JSON):
        with open(VERSION_JSON) as f:
            version_json_data = json.load(f)
        old_ver = version_json_data.get("version")
        if old_ver != source_ver:
            version_json_data["version"] = source_ver
            version_json_data["release_date"] = "2026-06-13"
            if "components" in version_json_data:
                version_json_data["components"]["laap_brain_kernel"] = source_ver
                version_json_data["components"]["v5_upgrade_engine"] = source_ver
                version_json_data["components"]["hermes_bridge"] = source_ver
            if not dry_run:
                with open(VERSION_JSON, 'w') as f:
                    json.dump(version_json_data, f, indent=2)
            changes.append(f"[{'dry:' if dry_run else ''}✓] VERSION.json → {source_ver}")

    # 4. v5_upgrade.py
    if os.path.isfile(V5_UPGRADE):
        with open(V5_UPGRADE) as f:
            content = f.read()
        new_content = re.sub(
            r'(V5_VERSION\s*=\s*)"[^"]+"',
            rf'\1"{source_ver}"',
            content
        )
        if new_content != content:
            if not dry_run:
                with open(V5_UPGRADE, 'w') as f:
                    f.write(new_content)
            changes.append(f"[{'dry:' if dry_run else ''}✓] v5_upgrade.py → {source_ver}")

    # 5. laap-hermes / laap-hermes-v5 headers
    for fname in ["laap-hermes", "laap-hermes-v5"]:
        fpath = os.path.join(ROOT, fname)
        if os.path.isfile(fpath):
            with open(fpath) as f:
                content = f.read()
            new_content = re.sub(
                r'(LAAP )V?\d+\.\d+\.?\d*',
                rf'\1{source_ver}',
                content
            )
            if new_content != content:
                if not dry_run:
                    with open(fpath, 'w') as f:
                        f.write(new_content)
                changes.append(f"[{'dry:' if dry_run else ''}✓] {fname} → {source_ver}")

    return changes


def print_status(scan_results: List[Tuple[str, str, str, str]]):
    """Pretty-print version scan results."""
    print(f"\n  {'='*55}")
    print(f"  LAAP Version Sync — Status Report")
    print(f"  {'='*55}")
    print()

    source = ""
    for f, field, ver, status in scan_results:
        if status == "source":
            source = ver
            print(f"  ★ Source: {ver}")
            print()
            break

    mismatches = 0
    for f, field, ver, status in scan_results:
        if status == "source":
            continue
        icon = "✓" if ver == source else "✗"
        short_f = os.path.basename(f) if f else "?"
        if ver != source:
            mismatches += 1
        print(f"  {icon} {short_f:25s} {field:30s} {ver}")

    print(f"\n  {'='*55}")
    if mismatches == 0:
        print(f"  ✓ All {sum(1 for _ in scan_results)-1} references match source ({source})")
    else:
        print(f"  ✗ {mismatches} mismatch(es) — run with --apply to fix")
    print(f"  {'='*55}\n")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--check" in args or len(args) == 0:
        results = scan_all_versions()
        print_status(results)

    if "--apply" in args:
        changes = sync_all(dry_run=False)
        print(f"\n  Applied {len(changes)} change(s):")
        for c in changes:
            print(f"    {c}")

    # Direct version set
    for arg in args:
        if re.match(r'^\d+\.\d+\.\d+$', arg):
            # Update source first
            with open(LAAP_BRAIN_INIT) as f:
                content = f.read()
            new_content = re.sub(
                r'(LAAP_VERSION\s*=\s*)"[^"]+"',
                rf'\1"{arg}"',
                content
            )
            if new_content != content:
                with open(LAAP_BRAIN_INIT, 'w') as f:
                    f.write(new_content)
                print(f"\n  ✓ Source updated to {arg}")

            # Sync everything
            changes = sync_all(target_version=arg, dry_run=False)
            print(f"  Synced {len(changes)} file(s):")
            for c in changes:
                print(f"    {c}")
            break

    if not args:
        print("  Usage:")
        print("    python laap-sync-version.py           → check all versions")
        print("    python laap-sync-version.py --apply    → sync from source")
        print("    python laap-sync-version.py --check    → check only")
        print("    python laap-sync-version.py 5.1.0      → set new version everywhere")
