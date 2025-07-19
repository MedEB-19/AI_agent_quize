import re
import logging
from typing import List, Dict, Optional

class ContentProcessor:
    def __init__(self):
        """Initialize the ContentProcessor"""
        pass
    
    def process_content(self, raw_content: str) -> str:
        """
        Process and clean the raw course content
        
        Args:
            raw_content (str): Raw course content
            
        Returns:
            str: Processed and cleaned content
        """
        if not raw_content or not isinstance(raw_content, str):
            return ""
        
        try:
            # Basic cleaning
            content = self._clean_text(raw_content)
            
            # Remove excessive whitespace
            content = self._normalize_whitespace(content)
            
            # Extract meaningful sections
            content = self._extract_meaningful_content(content)
            
            # Validate processed content
            if len(content.strip()) < 50:
                logging.warning("Processed content is very short")
                return raw_content.strip()  # Return original if processing made it too short
            
            return content
            
        except Exception as e:
            logging.error(f"Error processing content: {str(e)}")
            return raw_content.strip()  # Return original content if processing fails
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove HTML tags if present
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\'\"]+', ' ', text)
        
        # Fix common formatting issues
        text = re.sub(r'\s*\n\s*\n\s*', '\n\n', text)  # Normalize paragraph breaks
        text = re.sub(r'\s*\.\s*\.\s*\.+', '...', text)  # Fix ellipses
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with maximum of two
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _extract_meaningful_content(self, text: str) -> str:
        """Extract and prioritize meaningful content"""
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Filter out very short paragraphs (likely not substantial content)
        meaningful_paragraphs = []
        for paragraph in paragraphs:
            # Keep paragraphs that are substantial or contain key information
            if (len(paragraph) > 20 or 
                self._contains_key_information(paragraph)):
                meaningful_paragraphs.append(paragraph)
        
        return '\n\n'.join(meaningful_paragraphs)
    
    def _contains_key_information(self, text: str) -> bool:
        """Check if text contains key educational information"""
        # Look for educational keywords and patterns
        key_patterns = [
            r'\b(define|definition|concept|principle|theory|method|process)\b',
            r'\b(example|instance|case|scenario|situation)\b',
            r'\b(important|significant|key|main|primary|essential)\b',
            r'\b(because|therefore|thus|consequently|as a result)\b',
            r'\b(first|second|third|next|then|finally)\b',
            r'\b(compare|contrast|difference|similar|unlike)\b'
        ]
        
        text_lower = text.lower()
        for pattern in key_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def extract_key_topics(self, content: str) -> List[str]:
        """
        Extract key topics from content for quiz generation variety
        
        Args:
            content (str): Course content
            
        Returns:
            List[str]: List of key topics/concepts
        """
        try:
            # Simple keyword extraction based on frequency and context
            words = re.findall(r'\b[A-Za-z]{4,}\b', content.lower())
            
            # Filter out common words
            common_words = {
                'that', 'this', 'with', 'from', 'they', 'them', 'have', 'been', 
                'were', 'said', 'each', 'which', 'their', 'time', 'will', 'about',
                'would', 'there', 'could', 'other', 'more', 'very', 'what', 'know',
                'just', 'first', 'into', 'over', 'think', 'than', 'only', 'come',
                'also', 'work', 'make', 'through', 'example', 'when', 'where'
            }
            
            # Count word frequency
            word_freq = {}
            for word in words:
                if word not in common_words and len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            key_topics = [word for word, freq in sorted_words[:10] if freq > 1]
            
            return key_topics
            
        except Exception as e:
            logging.error(f"Error extracting key topics: {str(e)}")
            return []
    
    def chunk_content(self, content: str, chunk_size: int = 500) -> List[str]:
        """
        Split content into chunks for processing
        
        Args:
            content (str): Content to chunk
            chunk_size (int): Approximate size of each chunk
            
        Returns:
            List[str]: List of content chunks
        """
        if not content:
            return []
        
        try:
            # Split by paragraphs first
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            chunks = []
            current_chunk = []
            current_size = 0
            
            for paragraph in paragraphs:
                para_size = len(paragraph)
                
                # If adding this paragraph would exceed chunk size, start new chunk
                if current_size + para_size > chunk_size and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [paragraph]
                    current_size = para_size
                else:
                    current_chunk.append(paragraph)
                    current_size += para_size
            
            # Add remaining content
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            return chunks
            
        except Exception as e:
            logging.error(f"Error chunking content: {str(e)}")
            return [content]  # Return original content as single chunk
    
    def validate_content(self, content: str) -> Dict[str, any]:
        """
        Validate content quality for quiz generation
        
        Args:
            content (str): Content to validate
            
        Returns:
            Dict containing validation results
        """
        validation = {
            'is_valid': False,
            'length': len(content),
            'word_count': 0,
            'has_structure': False,
            'has_concepts': False,
            'issues': []
        }
        
        try:
            if not content or len(content.strip()) < 50:
                validation['issues'].append('Content too short')
                return validation
            
            # Count words
            words = re.findall(r'\b\w+\b', content)
            validation['word_count'] = len(words)
            
            if validation['word_count'] < 20:
                validation['issues'].append('Too few words')
                return validation
            
            # Check for structure (paragraphs, sentences)
            paragraphs = content.split('\n\n')
            sentences = re.split(r'[.!?]+', content)
            
            if len(paragraphs) > 1 and len(sentences) > 3:
                validation['has_structure'] = True
            
            # Check for educational concepts
            concept_indicators = [
                'define', 'concept', 'theory', 'principle', 'method',
                'example', 'because', 'therefore', 'important', 'process'
            ]
            
            content_lower = content.lower()
            for indicator in concept_indicators:
                if indicator in content_lower:
                    validation['has_concepts'] = True
                    break
            
            # Overall validation
            if (validation['word_count'] >= 20 and 
                validation['has_structure'] and 
                len(validation['issues']) == 0):
                validation['is_valid'] = True
            
            return validation
            
        except Exception as e:
            logging.error(f"Error validating content: {str(e)}")
            validation['issues'].append('Validation error')
            return validation
