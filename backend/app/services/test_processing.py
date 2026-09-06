import sys
from pathlib import Path

from app.services.document_processor import (
    process_document
)


project_root = Path(__file__).resolve().parents[2]
uploads_dir = project_root / "uploads"

if len(sys.argv) > 1:
    file_path = Path(sys.argv[1])
    if not file_path.is_absolute():
        file_path = project_root / file_path
else:
    uploaded_files = sorted(uploads_dir.glob("*.pdf"))
    if not uploaded_files:
        raise FileNotFoundError(
            f"No PDF files found in {uploads_dir}"
        )
    file_path = uploaded_files[0]


chunks = process_document(
    str(file_path)
)

print(
    f"Total chunks: {len(chunks)}"
)

for index, chunk in enumerate(
    chunks[:5]
):

    print("\n----------------")
    print(f"Chunk: {index + 1}")
    print("----------------")

    print(
        chunk.page_content[:500]
    )

    print(
        "Metadata:",
        chunk.metadata
    )