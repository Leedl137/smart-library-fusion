#!/usr/bin/env python3
"""
生成项目架构图脚本 (gpt-image-2 via apiyi中转站)
用法: python scripts/generate_arch_images.py
"""
import base64
import os
import urllib3
from openai import OpenAI

urllib3.disable_warnings()

API_KEY = "sk-0Yv1Gxq3cp1RDrm89e168cD19a9e48F6B51223A3B2B24056"
BASE_URL = "https://api.apiyi.com/v1"
OUTPUT_DIR = "report_assets"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    http_client=__import__("httpx").Client(verify=False),
)

prompts = [
    (
        "architecture_layers.png",
        "A clean modern professional system architecture diagram for a university library management system. "
        "Four horizontal layers stacked vertically with elegant connecting arrows. "
        "Top layer light blue: Vue3 frontend, Element Plus UI, ECharts visualization dashboard. "
        "Second layer light green: FastAPI routers, JWT auth, RBAC+ABAC permissions, SQL Guard security. "
        "Third layer light orange: Book borrowing management, access control, seat reservation, AI NL2SQL Q&A service. "
        "Bottom layer light purple: MySQL 8.0 database, SQLAlchemy ORM, 15.45 million real library records. "
        "Rounded rectangles, minimalist flat design, tech blue color scheme, white background, professional infographic style.",
    ),
    (
        "ai_flow_diagram.png",
        "A clean modern flowchart showing AI-powered natural language to SQL query system. "
        "Horizontal left-to-right pipeline with 5 connected stages in rounded rectangles: "
        "1) User inputs natural language question, "
        "2) System prompt injection with security constraints, "
        "3) Large language model converts NL to SQL (NL2SQL), "
        "4) SQL Guard validates with regex blacklist (blocks DROP DELETE INSERT UPDATE ALTER), "
        "5) Read-only database account executes query with auto LIMIT injection. "
        "Below the main flow, show 4 security shield icons labeled: Prompt Constraints, Regex Validation, Read-only Account, LIMIT Control. "
        "Minimalist flat design, clean rounded rectangles, soft gradients, white background, tech infographic.",
    ),
    (
        "etl_pipeline.png",
        "A clean modern data flow diagram showing ETL pipeline for university library database system. "
        "Left side source data blocks in light blue: Book catalog CSV 450K records, Reader info CSV 57K, Borrow records CSV 1.9M, "
        "Access logs TXT 8.9M, Seat logs TXT 3.9M, Academic articles Excel 79K. "
        "Center large orange rounded rectangle: ETL Engine with inner steps Extract -> Clean -> Transform -> Load. "
        "Right side target database blocks in light purple: books table, users table, borrow_records table, "
        "access_logs table, seat_logs table, articles table. "
        "Arrows flow from left sources through center ETL engine to right targets. "
        "Minimalist flat design, rounded rectangles, soft pastel colors, white background, professional infographic.",
    ),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for filename, prompt in prompts:
        out_path = os.path.join(OUTPUT_DIR, filename)
        print(f"Generating {filename} ...")
        resp = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            n=1,
            size="1792x1024",
        )
        b64 = resp.data[0].b64_json
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64))
        print(f"  Saved: {out_path} ({os.path.getsize(out_path) // 1024} KB)")
    print("All done!")


if __name__ == "__main__":
    main()
