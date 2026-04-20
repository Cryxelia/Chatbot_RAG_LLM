import fitz 
import tiktoken
import re
from .sections import SECTION_HEADERS
import logging

logger = logging.getLogger("rag")

def extract_text_from_pdf(path):
    try:
        doc = fitz.open(path) #Open PDF file
        pages_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            text = re.sub(r"\n\s*\n", "\n\n", text).strip()
            pages_text.append(text)
        doc.close()
        return pages_text
    except Exception as e:
        logger.error(f"Fel vid läsning av PDF '{path}': {e}")
        return ""


SECTION_REGEX = re.compile("|".join(SECTION_HEADERS), re.MULTILINE) # Creating a regex that search for headers

def split_into_sections(text):
    """
        Divide the text into parts based on headings.
    """
    try:
        sections = []
        matches = list(SECTION_REGEX.finditer(text))
        logger.info(f"Hittade {len(matches)} rubriker i PDF:n")

        if not matches:
            logger.error("Ingen rubrik hittades")
            return [text]
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 <  len(matches) else len(text)
            section = text[start:end].strip()
            sections.append(section)
        
        return sections
    except Exception as e:
        logger.error(f"Fel vid uppdelning i sektioner: {e}")
        return []

try:
    enc = tiktoken.get_encoding("cl100k_base") # Initiate tinktonken qith encoding
except Exception as e:
    logger.error(f"Fel vid initiering av tokenizer: {e}")
    enc = None

def count_tokens(text):
    try:
        if enc is None:
            return max(1, len(text) // 4) 
        return len(enc.encode(text))
    except Exception as e:
        logger.error(f"Fel vid tokenräkning: {e}")
        return max(1, len(text) // 4)


def chunk_text(text, max_tokens=400, overlap_tokens=100):
    try:
        sentences = re.split(r'(?<!\d)\.(?=\s+[A-ZÅÄÖ])|(?<=[!?])\s+', text)  # Sliting text into sentences with regex
        chunks = []
        current_chunk = "" 
        current_tokens = 0

        for sent in sentences: # counting tokens in sentences
            sent_tokens = count_tokens(sent)

            if current_tokens + sent_tokens > max_tokens:
                chunks.append(current_chunk.strip())

                overlap_length = min(overlap_tokens, count_tokens(current_chunk))
                if enc:
                    tokens = enc.encode(current_chunk)
                    overlap = enc.decode(tokens[-overlap_length:])
                else:   
                    overlap = " ".join(current_chunk.split()[-overlap_length:])
                
                current_chunk = overlap + " " + sent
                current_tokens = count_tokens(current_chunk)
            else:
                current_chunk += " " + sent
                current_tokens += sent_tokens
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks # Return a list object  with chunks
    except Exception  as e:
        logger.error(f"Fel vid chunking: {e}")
        return [text] 


def process_pdf_to_chunks(pdf_path):
    """
        Use the functions above:
        1. Read text from PDF 
        2. Divide the text into sections
        3. Divide each section into chunks by chunk_text. 
        4. Collect all the chunks in all_chunks.
        5. Return the list of chunks.
    """
    try:
        pages = extract_text_from_pdf(pdf_path)
        all_chunks = []
        pdf_filename = pdf_path.split("/")[-1]

        for page_num, page_text in enumerate(pages, start=1):
            page_chunks = chunk_text(page_text, max_tokens=1000, overlap_tokens=100)
            
            for chunk_text_item in page_chunks:
                chunk = {
                    "text": chunk_text_item,
                    "source_pdf": pdf_filename,
                    "page_number": page_num
                }
                all_chunks.append(chunk)
        
        return all_chunks
    except Exception as e:
        logger.error(f"Fel vid bearbetning av PDF '{pdf_path}': {e}")
        return []