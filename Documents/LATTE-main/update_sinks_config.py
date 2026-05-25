#!/usr/bin/env python2
import argparse
import json
import os
import re
import sys
import io

try:
    basestring  # type: ignore
except NameError:  # pragma: no cover
    basestring = str  # py3 fallback if someone runs it there


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "lib")
if os.path.isdir(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

try:
    import yaml  # LATTE bundled yaml / PyYAML in your environment
except Exception as e:  # pragma: no cover
    raise SystemExit("Failed to import yaml: %r" % (e,))

def _load_text_file(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_json_file(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _iter_files(root, suffix):
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(suffix):
                yield os.path.join(base, name)


def _clean_model_text(s):
    s = s.strip()
    fence = "`" * 3
    if s.startswith(fence):
        s = re.sub(r"^" + re.escape(fence) + r"(?:json)?\s*", "", s, flags=re.IGNORECASE)
    if s.endswith(fence):
        s = re.sub(r"\s*" + re.escape(fence) + r"$", "", s)
    return s.strip()


def _try_parse_as_json_pairs(s):
    """
    Tries to parse model output as JSON-like structures.
    Supports:
      - ["func", 1]
      - [["func", 1], ["other", 2]]
      - [{"function":"strcpy","param":1}, ...] (best-effort)
    """
    s = _clean_model_text(s)
    if not s:
        return None
    try:
        obj = json.loads(s)
    except Exception:
        return None

    out = []

    def add(func, params):
        func = ("%s" % func).strip()
        if not func:
            return
        ps = []
        for p in params:
            try:
                ps.append(int(p))
            except Exception:
                continue
        if ps:
            out.append((func, ps))

    if isinstance(obj, list):
        # single pair: ["strcpy", 1]
        if len(obj) >= 2 and not isinstance(obj[1], (list, dict)):
            add(obj[0], [obj[1]])
            return out or None

        # list of pairs: [["strcpy",1],["snprintf",2]]
        for item in obj:
            if isinstance(item, list) and len(item) >= 2:
                add(item[0], [item[1]])
            elif isinstance(item, dict):
                func = item.get("function") or item.get("func") or item.get("name")
                param = item.get("param") or item.get("arg") or item.get("index")
                if func is not None and param is not None:
                    add(func, [param])
        return out or None

    if isinstance(obj, dict):
        # {"strcpy":[1], "snprintf":[1,2]}
        for k, v in obj.items():
            if isinstance(v, list):
                params = []
                for x in v:
                    try:
                        params.append(int(x))
                    except Exception:
                        continue
                if params:
                    out.append(("%s" % k, params))
        return out or None

    return None


def _parse_bracket_pairs_fallback(s):
    """
    Fallback parser for model outputs like:
      [strcpy, 1]
      [ strcpy , 1 ], [ snprintf, 2 ]
    """
    s = _clean_model_text(s)
    if not s:
        return []

    pairs = []
    for inner in re.findall(r"\[([^\[\]]+)\]", s):
        parts = [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
        if len(parts) < 2:
            continue
        func = parts[0]
        params = []
        for p in parts[1:2]:  # only the first parameter index is expected by ask_source_dest.py prompt
            try:
                params.append(int(p))
            except Exception:
                continue
        if func and params:
            pairs.append((func, params))
    return pairs


def extract_sink_pairs_from_srdst_payload(payload):
    """
    payload is typically: ["Source: ...; Sink: ..."] (list[str])
    """
    if isinstance(payload, basestring):
        text = payload
    elif isinstance(payload, list):
        text = "\n".join([("%s" % x) for x in payload])
    else:
        text = "%s" % payload

    # Prefer text after "Sink:" if present
    m = re.search(r"Sink\s*:\s*(.*)$", text, flags=re.IGNORECASE | re.DOTALL)
    sink_text = m.group(1).strip() if m else text.strip()

    parsed = _try_parse_as_json_pairs(sink_text)
    if parsed:
        return parsed
    return _parse_bracket_pairs_fallback(sink_text)


def merge_sink_functions(
    base,
    adds,
    replace,
):
    out = {}
    if not replace:
        for k, v in (base or {}).items():
            s = set()
            if isinstance(v, list):
                for x in v:
                    try:
                        s.add(int(x))
                    except Exception:
                        continue
            out["%s" % k] = s

    for func, params in adds.items():
        out.setdefault(func, set()).update(params)

    result = {}
    for k, v in out.items():
        if not v:
            continue
        result[k] = sorted(list(v))
    return result


def main():
    ap = argparse.ArgumentParser(
        description="Batch read ask_source_dest.py outputs (*-srdst.json) and update config.yaml sink_functions."
    )
    ap.add_argument("--input-dir", required=True, help="Directory containing *-srdst.json files (walked recursively).")
    ap.add_argument("--config", default=os.path.join(SCRIPT_DIR, "config.yaml"), help="Path to config.yaml to update.")
    ap.add_argument("--suffix", default="-srdst.json", help="Filename suffix to match (default: -srdst.json).")
    ap.add_argument("--replace", action="store_true", help="Replace sink_functions instead of merging.")
    ap.add_argument("--dry-run", action="store_true", help="Do not write config.yaml; print summary only.")
    args = ap.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    config_path = os.path.abspath(args.config)

    if not os.path.isdir(input_dir):
        sys.stderr.write("ERROR: input dir not found: %s\n" % input_dir)
        return 2
    if not os.path.isfile(config_path):
        sys.stderr.write("ERROR: config file not found: %s\n" % config_path)
        return 2

    with io.open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        cfg = {}
    base_sink = cfg.get("sink_functions", {})
    if not isinstance(base_sink, dict):
        base_sink = {}

    collected = {}
    parsed_files = 0
    parsed_pairs = 0

    for path in _iter_files(input_dir, args.suffix):
        parsed_files += 1
        try:
            payload = _load_json_file(path)
        except Exception:
            # best-effort: try read raw text then json.loads
            try:
                payload = json.loads(_load_text_file(path))
            except Exception:
                continue

        pairs = extract_sink_pairs_from_srdst_payload(payload)
        for func, params in pairs:
            parsed_pairs += 1
            for p in params:
                collected.setdefault(func, set()).add(int(p))

    merged = merge_sink_functions(base_sink, collected, replace=bool(args.replace))

    if args.dry_run:
        print("Matched files: %d" % parsed_files)
        print("Extracted pairs: %d" % parsed_pairs)
        print("Unique sink functions added: %d" % len(collected))
        print("Resulting sink_functions size: %d" % len(merged))
        return 0

    cfg["sink_functions"] = merged
    with io.open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True)
    print("Updated: %s" % config_path)
    print("Matched files: %d" % parsed_files)
    print("Extracted pairs: %d" % parsed_pairs)
    print("Resulting sink_functions size: %d" % len(merged))
    return 0


if __name__ == "__main__":
    sys.exit(main())

