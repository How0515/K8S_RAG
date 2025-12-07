"""
PDF 처리 모듈
- PDF 파일에서 텍스트 추출
- 텍스트 청킹
"""

from pypdf import PdfReader
from typing import List
import io


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDF 바이트에서 텍스트 추출"""
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    텍스트를 청크로 분할
    
    Args:
        text: 원본 텍스트
        chunk_size: 청크 크기 (문자 수)
        overlap: 청크 간 오버랩 (문자 수)
    
    Returns:
        청크 리스트
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # 문장 경계에서 자르기 시도
        if end < text_length:
            # 마침표, 물음표, 느낌표 찾기
            for sep in ['. ', '? ', '! ', '\n']:
                last_sep = text.rfind(sep, start, end)
                if last_sep != -1:
                    end = last_sep + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end - overlap > start else end
    
    return chunks
