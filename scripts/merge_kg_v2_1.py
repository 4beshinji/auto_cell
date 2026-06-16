#!/usr/bin/env python3
"""Merge knowledge_graph_v2.json + additional_investigation_diff.json -> v2.1 artifacts."""
import json
import csv
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
KG_DIR = ROOT / "docs" / "knowledge_graph"
GEN_DIR = KG_DIR / "generated"

BASE_KG_PATH = KG_DIR / "knowledge_graph_v2.json"
DIFF_PATH = GEN_DIR / "additional_investigation_diff.json"

OUT_JSON = KG_DIR / "knowledge_graph_v2_1.json"
OUT_JSONL = KG_DIR / "knowledge_graph_v2_1.jsonl"
OUT_TTL = KG_DIR / "knowledge_graph_v2_1.ttl"
OUT_NODES_CSV = KG_DIR / "nodes_v2_1.csv"
OUT_EDGES_CSV = KG_DIR / "edges_v2_1.csv"
OUT_SOURCES_CSV = KG_DIR / "sources_v2_1.csv"
OUT_HTML = KG_DIR / "ips_automation_knowledge_map_v2_1.html"
TEMPLATE_HTML = KG_DIR / "ips_automation_knowledge_map_v2.html"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_nodes(base_nodes, diff_nodes):
    """Keep base as canonical. On ID conflict, merge additional diff properties into base."""
    by_id = {n["id"]: dict(n) for n in base_nodes}
    conflicts = []
    for dn in diff_nodes:
        nid = dn["id"]
        if nid in by_id:
            conflicts.append(nid)
            bn = by_id[nid]
            # Merge additional keys from diff, but keep base values for existing keys.
            for k, v in dn.items():
                if k not in bn:
                    bn[k] = v
            # For source nodes specifically, merge sources arrays if diff adds new sources.
            if isinstance(dn.get("sources"), list):
                existing_urls = {s.get("url") for s in bn.get("sources", []) if isinstance(s, dict)}
                for s in dn["sources"]:
                    if isinstance(s, dict) and s.get("url") not in existing_urls:
                        bn.setdefault("sources", []).append(s)
                        existing_urls.add(s.get("url"))
        else:
            by_id[nid] = dict(dn)
    return list(by_id.values()), conflicts


def normalize_edge(e):
    return (e.get("source") or e.get("s"), e.get("rel"), e.get("target") or e.get("t"))


def merge_edges(base_edges, diff_edges):
    seen = set()
    merged = []
    dupes = []
    for e in base_edges:
        key = normalize_edge(e)
        if key not in seen:
            seen.add(key)
            merged.append(dict(e))
    for e in diff_edges:
        key = normalize_edge(e)
        if key in seen:
            dupes.append(key)
        else:
            seen.add(key)
            merged.append({"source": key[0], "rel": key[1], "target": key[2]})
    return merged, dupes


def merge_sources(base_sources, diff_sources):
    by_id = {s["id"]: dict(s) for s in base_sources}
    conflicts = []
    for ds in diff_sources:
        sid = ds["id"]
        if sid in by_id:
            conflicts.append(sid)
            bs = by_id[sid]
            for k, v in ds.items():
                if k not in bs:
                    bs[k] = v
        else:
            by_id[sid] = dict(ds)
    return list(by_id.values()), conflicts


def build_domain_label_map(domains):
    return {d["id"]: d.get("label", "") for d in domains}


def validate(kg):
    errors = []
    node_ids = {n["id"] for n in kg["nodes"]}

    missing_endpoints = []
    for e in kg["edges"]:
        s = e.get("source") or e.get("s")
        t = e.get("target") or e.get("t")
        if s not in node_ids:
            missing_endpoints.append(("source", s, e))
        if t not in node_ids:
            missing_endpoints.append(("target", t, e))
    if missing_endpoints:
        errors.append(f"Edges with missing endpoints: {len(missing_endpoints)}")

    connected = set()
    for e in kg["edges"]:
        connected.add(e.get("source") or e.get("s"))
        connected.add(e.get("target") or e.get("t"))
    isolated = [n["id"] for n in kg["nodes"] if n["id"] not in connected]
    if isolated:
        errors.append(f"Isolated nodes: {len(isolated)} -> {isolated[:10]}")

    # Source nodes referenced by edges or by node.sources
    referenced_sources = set()
    for e in kg["edges"]:
        s = e.get("source") or e.get("s")
        t = e.get("target") or e.get("t")
        if any(n["id"] == s and n["type"] == "source" for n in kg["nodes"]):
            referenced_sources.add(s)
        if any(n["id"] == t and n["type"] == "source" for n in kg["nodes"]):
            referenced_sources.add(t)
    source_node_ids = {n["id"] for n in kg["nodes"] if n["type"] == "source"}
    unreferenced_sources = source_node_ids - referenced_sources
    if unreferenced_sources:
        errors.append(f"Unreferenced source nodes: {len(unreferenced_sources)} -> {list(unreferenced_sources)[:10]}")

    # Check canonical source IDs referenced by nodes
    canonical_ids = {s["id"] for s in kg["sources"]}
    source_url_to_id = {s["url"]: s["id"] for s in kg["sources"] if s.get("url")}
    referenced_canonical = set()
    for n in kg["nodes"]:
        for s in n.get("sources", []):
            if isinstance(s, dict):
                url = s.get("url")
                if url in source_url_to_id:
                    referenced_canonical.add(source_url_to_id[url])
    unreferenced_canonical = canonical_ids - referenced_canonical
    if unreferenced_canonical:
        errors.append(f"Canonical sources not referenced by any node: {len(unreferenced_canonical)} -> {list(unreferenced_canonical)[:10]}")

    return errors, {
        "missing_endpoints_count": len(missing_endpoints),
        "isolated_count": len(isolated),
        "isolated_sample": isolated[:10],
        "unreferenced_source_nodes_count": len(unreferenced_sources),
        "unreferenced_source_nodes_sample": list(unreferenced_sources)[:10],
        "unreferenced_canonical_sources_count": len(unreferenced_canonical),
        "unreferenced_canonical_sources_sample": list(unreferenced_canonical)[:10],
    }


def write_json(kg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)


def write_jsonl(kg, path):
    with open(path, "w", encoding="utf-8") as f:
        for n in kg["nodes"]:
            row = dict(n)
            row["_kind"] = "node"
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        for e in kg["edges"]:
            row = {"source": e.get("source") or e.get("s"),
                   "target": e.get("target") or e.get("t"),
                   "rel": e.get("rel"),
                   "_kind": "edge"}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_nodes_csv(kg, path):
    domain_labels = build_domain_label_map(kg["domains"])
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "label", "type", "domain", "domain_label", "content", "source_count"])
        for n in kg["nodes"]:
            domain = n.get("domain") or ""
            writer.writerow([
                n["id"],
                n.get("label", ""),
                n.get("type", ""),
                domain if domain else "",
                domain_labels.get(domain, ""),
                n.get("content", ""),
                len(n.get("sources", [])),
            ])


def write_edges_csv(kg, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "rel", "target"])
        for e in kg["edges"]:
            writer.writerow([
                e.get("source") or e.get("s"),
                e.get("rel", ""),
                e.get("target") or e.get("t"),
            ])


def write_sources_csv(kg, path):
    # referenced_by_nodes: collect node ids whose node.sources url matches canonical source url
    ref_map = defaultdict(list)
    for n in kg["nodes"]:
        for s in n.get("sources", []):
            if isinstance(s, dict) and s.get("url"):
                ref_map[s["url"]].append(n["id"])
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_url", "source_title", "referenced_by_nodes"])
        for s in kg["sources"]:
            refs = ";".join(sorted(set(ref_map.get(s.get("url", ""), []))))
            writer.writerow([s.get("url", ""), s.get("title", ""), refs])


def ttl_escape(s):
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def write_ttl(kg, path):
    lines = [
        "@prefix : <https://tangletech.dev/ips-automation-kg#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix dct: <http://purl.org/dc/terms/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        ":Concept a rdfs:Class .",
        ":Domain a rdfs:Class .",
        ":Player a rdfs:Class .",
        ":Root a rdfs:Class .",
        ":Source a rdfs:Class .",
        ":System a rdfs:Class .",
        "",
    ]
    type_map = {
        "root": ":Root",
        "domain": ":Domain",
        "concept": ":Concept",
        "system": ":System",
        "player": ":Player",
        "source": ":Source",
    }
    for n in kg["nodes"]:
        nid = "n_" + re.sub(r"[^a-zA-Z0-9_]", "_", n["id"])
        cls = type_map.get(n.get("type"), ":Concept")
        lines.append(f"{nid} a {cls} ;")
        lines.append(f'    rdfs:label "{ttl_escape(n.get("label", ""))}"@ja ;')
        if n.get("domain"):
            lines.append(f"    :inDomain :n_{re.sub(r'[^a-zA-Z0-9_]', '_', n['domain'])} ;")
        if n.get("content"):
            lines.append(f'    :content "{ttl_escape(n.get("content", ""))}"@ja ;')
        sources = n.get("sources", [])
        if sources:
            src_lines = []
            for s in sources:
                if isinstance(s, dict):
                    url = s.get("url", "")
                    title = s.get("title", "")
                    if url:
                        src_lines.append(f'[ dct:title "{ttl_escape(title)}"@ja ; :url <{url}> ]')
                    else:
                        src_lines.append(f'[ dct:title "{ttl_escape(title)}"@ja ]')
            if src_lines:
                lines.append("    :hasSource " + " ,\n               ".join(src_lines) + " ;")
        lines.append("    .")
        lines.append("")

    rel_map = {
        "contains": ":contains",
        "has": ":has",
    }
    for e in kg["edges"]:
        s = e.get("source") or e.get("s")
        t = e.get("target") or e.get("t")
        rel = e.get("rel", "")
        s_uri = ":n_" + re.sub(r"[^a-zA-Z0-9_]", "_", s)
        t_uri = ":n_" + re.sub(r"[^a-zA-Z0-9_]", "_", t)
        pred = rel_map.get(rel, ":rel_" + re.sub(r"[^a-zA-Z0-9_]", "_", rel))
        lines.append(f"{s_uri} {pred} {t_uri} .")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def js_literal_string(s):
    return json.dumps(s, ensure_ascii=False)


def write_html(kg, template_path, out_path):
    template = template_path.read_text(encoding="utf-8")

    # Domains array (with colors)
    color_map = {
        "d1": "--d1", "d2": "--d2", "d3": "--d3", "d4": "--d4",
        "d5": "--d5", "d6": "--d6", "d7": "--d7", "d8": "--d8",
    }
    def domain_color(d):
        return color_map.get(d['id'], d.get('color', "--" + d['id']))

    domains_js = "[\n" + ",\n".join(
        "  {id:" + js_literal_string(d['id']) + ",label:" + js_literal_string(d.get('label', '')) + ",color:" + js_literal_string(domain_color(d)) + "}"
        for d in kg["domains"]
    ) + "\n]"

    # Nodes array: {id,label,type,domain,content,sources:[{t,u}]}
    def src_str(s):
        return "{t:" + js_literal_string(s.get("title", "")) + ",u:" + js_literal_string(s.get("url", "")) + "}"

    nodes_js = "[\n" + ",\n".join(
        "  {id:" + js_literal_string(n["id"]) +
        ",label:" + js_literal_string(n.get("label", "")) +
        ",type:" + js_literal_string(n.get("type", "")) +
        ",domain:" + (js_literal_string(n["domain"]) if n.get("domain") else "null") +
        ",content:" + js_literal_string(n.get("content", "")) +
        ",sources:[" + ",".join(src_str(s) for s in n.get("sources", []) if isinstance(s, dict)) + "]}"
        for n in kg["nodes"]
    ) + "\n]"

    # Edges array: {s,t,rel}
    edges_js = "[\n" + ",\n".join(
        f"  {{s:{js_literal_string(e.get('source') or e.get('s'))},t:{js_literal_string(e.get('target') or e.get('t'))},rel:{js_literal_string(e.get('rel', ''))}}}"
        for e in kg["edges"]
    ) + "\n]"

    # Replace const DOMAINS = [...];
    template = re.sub(
        r"const DOMAINS = \[.*?\];",
        f"const DOMAINS = {domains_js};",
        template,
        flags=re.DOTALL,
        count=1,
    )
    # Replace const NODES = [...];
    template = re.sub(
        r"const NODES = \[.*?\];",
        f"const NODES = {nodes_js};",
        template,
        flags=re.DOTALL,
        count=1,
    )
    # Replace const EDGES = [...];
    template = re.sub(
        r"const EDGES = \[.*?\];",
        f"const EDGES = {edges_js};",
        template,
        flags=re.DOTALL,
        count=1,
    )
    # Update title
    template = template.replace(
        "iPS自動培養ソフトウェア｜ドメイン知識マップ v2",
        "iPS自動培養ソフトウェア｜ドメイン知識マップ v2.1",
    )

    out_path.write_text(template, encoding="utf-8")


def main():
    base = load_json(BASE_KG_PATH)
    diff = load_json(DIFF_PATH)

    base_counts = {
        "nodes": len(base["nodes"]),
        "edges": len(base["edges"]),
        "sources": len(base["sources"]),
    }

    merged_nodes, node_conflicts = merge_nodes(base["nodes"], diff["nodes"])
    merged_edges, edge_duplicates = merge_edges(base["edges"], diff["edges"])
    merged_sources, source_conflicts = merge_sources(base["sources"], diff["sources"])

    kg = {
        "meta": {
            **base.get("meta", {}),
            "title": "iPS自動培養ソフトウェア ドメイン知識マップ v2.1",
            "description": (
                base["meta"].get("description", "") +
                " [2026-06-16 v2.1: merged additional_investigation_diff.json]"
            ),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "node_count": len(merged_nodes),
            "edge_count": len(merged_edges),
            "source_count": len(merged_sources),
            "merged_from": [
                "docs/knowledge_graph/knowledge_graph_v2.json",
                str(DIFF_PATH.relative_to(ROOT)),
            ],
            "base_counts": base_counts,
            "diff_counts": diff["meta"].get("counts", {}),
        },
        "domains": base["domains"],
        "nodes": merged_nodes,
        "edges": merged_edges,
        "sources": merged_sources,
    }

    errors, details = validate(kg)

    write_json(kg, OUT_JSON)
    write_jsonl(kg, OUT_JSONL)
    write_ttl(kg, OUT_TTL)
    write_nodes_csv(kg, OUT_NODES_CSV)
    write_edges_csv(kg, OUT_EDGES_CSV)
    write_sources_csv(kg, OUT_SOURCES_CSV)
    write_html(kg, TEMPLATE_HTML, OUT_HTML)

    summary = {
        "base_counts": base_counts,
        "diff_counts": diff["meta"].get("counts", {}),
        "merged_counts": {
            "nodes": len(merged_nodes),
            "edges": len(merged_edges),
            "sources": len(merged_sources),
        },
        "node_conflicts": node_conflicts,
        "edge_duplicates_count": len(edge_duplicates),
        "edge_duplicates_sample": [list(t) for t in edge_duplicates[:10]],
        "source_conflicts": source_conflicts,
        "validation_errors": errors,
        "validation_details": details,
        "created_files": [
            str(p.relative_to(ROOT)) for p in [
                OUT_JSON, OUT_JSONL, OUT_TTL,
                OUT_NODES_CSV, OUT_EDGES_CSV, OUT_SOURCES_CSV,
                OUT_HTML,
            ]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    main()
