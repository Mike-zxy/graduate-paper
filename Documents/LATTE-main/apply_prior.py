#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Merge a prior library YAML into `config.yaml`.

Designed for this repo's Python2 environment and bundled yaml.

Examples:
  python2 apply_prior.py --prior priors/CWE_78_file.yaml --config config.yaml --dry-run
  python2 apply_prior.py --prior priors/CWE_78_file.yaml --config config.yaml
  python2 apply_prior.py --prior priors/CWE_78_file.yaml --config config.yaml --replace
"""
import argparse
import io
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "lib"))

try:
    import yaml
except Exception as e:
    raise SystemExit("Failed to import yaml (ensure `lib/` is on sys.path): %r" % (e,))


def _load_yaml(path):
    with io.open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping (dict): %s" % path)
    return data


def _dump_yaml(path, data):
    with io.open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def _merge_dict_of_lists(dst, src, replace):
    """
    For sink_functions / taint_labels style:
      key -> list[int|str]
    """
    if replace:
        # overwrite keys from src; keep other keys not in src
        out = dict(dst)
        for k, v in src.items():
            out[k] = v
        return out

    out = dict(dst)
    for k, v in src.items():
        if k not in out or out[k] is None:
            out[k] = v
            continue
        # merge lists (dedupe)
        if isinstance(out[k], list) and isinstance(v, list):
            seen = set()
            merged = []
            for x in out[k] + v:
                try:
                    key = int(x)
                except Exception:
                    key = "%s" % x
                if key in seen:
                    continue
                seen.add(key)
                merged.append(x)
            out[k] = merged
        else:
            # if shapes mismatch, src wins
            out[k] = v
    return out


def _merge_list(dst, src, replace):
    if replace:
        return list(src)
    out = []
    seen = set()
    for x in (dst or []) + (src or []):
        k = "%s" % x
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def merge_config(base_cfg, prior_cfg, replace):
    """
    Merge only known LATTE keys by default; keep any extra keys from both sides.
    """
    out = dict(base_cfg)

    # sink_functions / taint_labels: dict[str] -> list
    for k in ("sink_functions", "taint_labels"):
        if k in prior_cfg:
            base_val = out.get(k, {}) if isinstance(out.get(k, {}), dict) else {}
            prior_val = prior_cfg.get(k, {}) if isinstance(prior_cfg.get(k, {}), dict) else {}
            out[k] = _merge_dict_of_lists(base_val, prior_val, replace=replace)

    # list keys
    for k in ("source_functions", "source_global_symbols"):
        if k in prior_cfg:
            base_val = out.get(k, []) if isinstance(out.get(k, []), list) else []
            prior_val = prior_cfg.get(k, []) if isinstance(prior_cfg.get(k, []), list) else []
            out[k] = _merge_list(base_val, prior_val, replace=replace)

    # keep extra metadata for downstream validation (doesn't affect latte.py)
    for k in prior_cfg.keys():
        if k in ("sink_functions", "taint_labels", "source_functions", "source_global_symbols"):
            continue
        if replace or k not in out:
            out[k] = prior_cfg[k]
        else:
            # attempt deep merge for simple dicts
            if isinstance(out.get(k), dict) and isinstance(prior_cfg.get(k), dict):
                merged = dict(out[k])
                merged.update(prior_cfg[k])
                out[k] = merged
            else:
                out[k] = prior_cfg[k]

    return out


def main():
    ap = argparse.ArgumentParser(description="Merge a prior YAML library into config.yaml (Python2).")
    ap.add_argument("--prior", required=True, help="Path to prior YAML (e.g. priors/CWE_78_file.yaml).")
    ap.add_argument("--config", default=os.path.join(SCRIPT_DIR, "config.yaml"), help="Path to config.yaml.")
    ap.add_argument("--replace", action="store_true", help="Replace values for matching keys (shallow).")
    ap.add_argument("--dry-run", action="store_true", help="Show summary only; do not write config.")
    args = ap.parse_args()

    prior_path = args.prior
    if not os.path.isabs(prior_path):
        prior_path = os.path.abspath(os.path.join(SCRIPT_DIR, prior_path))
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.abspath(os.path.join(SCRIPT_DIR, config_path))

    if not os.path.isfile(prior_path):
        sys.stderr.write("ERROR: prior file not found: %s\n" % prior_path)
        return 2
    if not os.path.isfile(config_path):
        sys.stderr.write("ERROR: config file not found: %s\n" % config_path)
        return 2

    base_cfg = _load_yaml(config_path)
    prior_cfg = _load_yaml(prior_path)

    merged = merge_config(base_cfg, prior_cfg, replace=bool(args.replace))

    if args.dry_run:
        def _len_or_zero(x):
            try:
                return len(x)
            except Exception:
                return 0
        print("Config: %s" % config_path)
        print("Prior : %s" % prior_path)
        print("Mode  : %s" % ("replace" if args.replace else "merge"))
        print("sink_functions: %d -> %d" % (_len_or_zero(base_cfg.get("sink_functions", {})), _len_or_zero(merged.get("sink_functions", {}))))
        print("taint_labels  : %d -> %d" % (_len_or_zero(base_cfg.get("taint_labels", {})), _len_or_zero(merged.get("taint_labels", {}))))
        print("source_functions: %d -> %d" % (_len_or_zero(base_cfg.get("source_functions", [])), _len_or_zero(merged.get("source_functions", []))))
        return 0

    _dump_yaml(config_path, merged)
    print("Updated config: %s" % config_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

