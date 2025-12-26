import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from app.services.document_loader import load_mlb_pdfs
    from app.services.rag_service import MLBKnowledgeRAG
except ImportError:
    from backend.app.services.document_loader import load_mlb_pdfs
    from backend.app.services.rag_service import MLBKnowledgeRAG


def main():
    """PDFをベクトルDBにインデックス化するメイン処理"""

    # PDFディレクトリのパス
    pdf_directory = project_root / "app" / "data" / "knowledge_base"
    logger.info(f"PDF directory: {pdf_directory}")

    # Step 1: load PDFs
    logger.info("Step 1: Loading PDFs...")
    documents = load_mlb_pdfs(str(pdf_directory))

    if not documents:
        logger.error("No documents loaded. Please check the PDF directory.")
        return
    
    logger.info(f"Loaded {len(documents)} documents")

    # Step 2: Initialize RAG service
    logger.info("Step 2: Initializing RAG service...")
    rag_service = MLBKnowledgeRAG()

    # Step 3: Index documents
    logger.info("Step 3: Indexing documents...")
    rag_service.index_documents(documents)

    # Step 4: Confirm indexing
    collection_count = rag_service.collection.count()
    logger.info(f"Indexing complete! Total documents in vector DB: {collection_count}")

if __name__ == "__main__":
    main()
