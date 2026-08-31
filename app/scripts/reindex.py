import argparse
import asyncio

from ..database import ensure_indexes, get_db
from ..services.rag_pipeline import reindex


async def main() -> None:
    parser = argparse.ArgumentParser(description="Build or update the portfolio RAG index")
    parser.add_argument("--force", action="store_true", help="Re-embed unchanged documents")
    parser.add_argument("--source", action="append", choices=["profile", "project", "field_note", "page", "site"], dest="sources")
    args = parser.parse_args()
    db = get_db()
    ensure_indexes(db)
    result = await reindex(db, source_types=args.sources, force=args.force)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
