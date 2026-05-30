import argparse
import sys
import uuid

from dotenv import load_dotenv

load_dotenv()

from app.graph.workflow import run_graph  # noqa: E402 — must load env first


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trade Finance Compliance — Document Extractor"
    )
    parser.add_argument(
        "documents",
        nargs="+",
        metavar="PDF",
        help="Paths to trade document PDFs (Bill of Lading, Invoice, Packing List)",
    )
    parser.add_argument(
        "--policy",
        default=None,
        metavar="PDF",
        help="Path to a bank policy PDF (optional)",
    )
    args = parser.parse_args()

    thread_id = str(uuid.uuid4())
    final_state = run_graph(
        document_paths=args.documents,
        policy_path=args.policy,
        thread_id=thread_id,
    )

    doc_data = final_state.get("document_data")
    if doc_data is None or doc_data.extraction_confidence == 0.0:
        print("Error: document extraction failed.", file=sys.stderr)
        if final_state.get("errors"):
            print(f"Errors: {final_state['errors']}", file=sys.stderr)
        sys.exit(1)

    print(doc_data.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
