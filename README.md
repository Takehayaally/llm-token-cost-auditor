# LLM Token Cost Auditor

Parse local JSONL LLM call logs, estimate cost from an editable pricing file, and flag expensive requests. This MVP keeps all logs local.

By TinyOps Tools. Support: q749381667@gmail.com.

## Usage

```powershell
python products/llm-token-cost-auditor/token_cost_auditor.py --logs products/llm-token-cost-auditor/examples/logs.jsonl --pricing products/llm-token-cost-auditor/examples/pricing.json --html-out products/llm-token-cost-auditor/examples/report.html --csv-out products/llm-token-cost-auditor/examples/report.csv
```

## Paid Bundle

Launch price: $19 on Gumroad. The paid bundle is planned to include anomaly rule presets, batch reporting examples, and a commercial-use license.
