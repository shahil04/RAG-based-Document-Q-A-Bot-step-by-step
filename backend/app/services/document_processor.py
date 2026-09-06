# Create Document Processor
from app.rag.loader import load_document
from app.rag.splitter import split_documents


def process_document(
    file_path: str
):

    documents = load_document(
        file_path
    )

    chunks = split_documents(
        documents
    )

    return chunks