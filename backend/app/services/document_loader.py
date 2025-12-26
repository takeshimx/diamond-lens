from PyPDF2 import PdfReader
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def load_mlb_pdfs(pdf_directory: str) -> List[Dict[str, str]]:
    """
    PDFファイルをテキストに変換してドキュメントリストを返す

    Args:
        pdf_directory: PDFファイルが格納されているディレクトリパス

    Returns:
        List[Dict[str, str]]: ドキュメントリスト
            - content: PDFから抽出したテキスト
            - source: ファイル名
            - type: ドキュメントタイプ
    """
    documents = []
    pdf_path = Path(pdf_directory)

    if not pdf_path.exists():
        logger.error(f"Directory does not exist: {pdf_directory}")
        return documents
    
    pdf_files = list(pdf_path.glob("*.pdf")) # ディレクトリ内の全PDFファイルを検索
    logger.info(f"Found {len(pdf_files)} PDF files in {pdf_directory}")

    for pdf_file in pdf_files:
        try:
            logger.info(f"Loading PDF: {pdf_file.name}")
            reader = PdfReader(pdf_file)

            text = ""
            for page_num, page in enumerate(reader.pages, start=1): # 各ページを1から番号付け
                page_text = page.extract_text()
                text += page_text
                logger.debug(f"Extracted {len(page_text)} characters from page {page_num}")
            
            if text.strip(): # 空白のみでないかチェック
                documents.append({
                    "content": text,
                    "source": pdf_file.name,
                    "type": "mlb_knowledge"
                })
                logger.warning(f"No text extracted from {pdf_file.name}")
        
        except Exception as e:
            logger.error(f"Error loading {pdf_file.name}: {e}", exc_info=True)
            continue # エラーが起きても他のPDFは処理続行
    
    logger.info(f"Successfully loaded {len(documents)} documents")
    return documents
            