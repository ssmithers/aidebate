import re


def extract_citations(text: str) -> tuple[str, list[dict]]:
    """
    Extract citations from text and replace with superscript references.
    
    Supports formats:
    - [Source: NASA]
    - (Source: Wikipedia)
    
    Returns:
        (cleaned_text, citations)
        - cleaned_text: Text with citations replaced by superscript numbers
        - citations: List of {id, text} dicts
    """
    citations = []
    citation_id = 1
    
    # Pattern 1: [Source: ...]
    pattern1 = r'\[Source:\s*([^\]]+)\]'
    
    # Pattern 2: (Source: ...)
    pattern2 = r'\(Source:\s*([^\)]+)\)'
    
    def replace_citation(match):
        nonlocal citation_id
        source_text = match.group(1).strip()
        citations.append({"id": citation_id, "text": source_text})
        result = f'<sup>[{citation_id}]</sup>'
        citation_id += 1
        return result
    
    # Replace both patterns
    cleaned = re.sub(pattern1, replace_citation, text)
    cleaned = re.sub(pattern2, replace_citation, cleaned)
    
    return cleaned, citations
