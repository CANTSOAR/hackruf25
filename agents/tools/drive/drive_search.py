"""
Google Drive Search Engine
Handles searching, content extraction, and relevance scoring for Drive files
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DriveFile:
    """Data class for Google Drive files"""
    id: str
    name: str
    mime_type: str
    web_view_link: str
    size: Optional[int]
    modified_time: Optional[str]
    parents: List[str]
    content: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None
    why_useful: Optional[str] = None

class DriveSearchEngine:
    """Handles Google Drive search and content extraction"""
    
    def __init__(self, service):
        """Initialize with authenticated Drive service"""
        self.service = service
        
        # File types that can be searched for content
        self.searchable_types = [
            'application/vnd.google-apps.document',  # Google Docs
            'application/vnd.google-apps.presentation',  # Google Slides
            'application/vnd.google-apps.spreadsheet',  # Google Sheets
            'application/pdf',  # PDF files
            'text/plain',  # Text files
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # Word docs
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PowerPoint
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # Excel
        ]
        
        # MIME types that can be exported as text
        self.exportable_types = [
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.presentation',
            'application/vnd.google-apps.spreadsheet'
        ]
    
    def search_files(self, query: str, max_results: int = 20, file_types: List[str] = None) -> List[DriveFile]:
        """
        Search for files in Google Drive
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            file_types: List of MIME types to filter by
            
        Returns:
            List of DriveFile objects
        """
        try:
            # Build search query
            search_params = [f"fullText contains '{query}'"]
            
            if file_types:
                # Filter by file types
                type_filter = " or ".join([f"mimeType='{mime}'" for mime in file_types])
                search_params.append(f"({type_filter})")
            
            # Add exclusion for trashed files
            search_params.append("trashed=false")
            
            search_query = " and ".join(search_params)
            
            # Execute search
            results = self.service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id,name,mimeType,webViewLink,size,modifiedTime,parents)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            drive_files = []
            
            for file_data in files:
                drive_file = DriveFile(
                    id=file_data['id'],
                    name=file_data['name'],
                    mime_type=file_data['mimeType'],
                    web_view_link=file_data['webViewLink'],
                    size=file_data.get('size'),
                    modified_time=file_data.get('modifiedTime'),
                    parents=file_data.get('parents', [])
                )
                drive_files.append(drive_file)
            
            return drive_files
            
        except HttpError as e:
            print(f"Drive search error: {e}")
            return []
        except Exception as e:
            print(f"Search failed: {e}")
            return []
    
    def extract_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """
        Extract text content from a Drive file
        
        Args:
            file_id: Google Drive file ID
            mime_type: MIME type of the file
            
        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            if mime_type in self.exportable_types:
                # Export Google Workspace files as text
                content = self.service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                return content.decode('utf-8')
            
            elif mime_type == 'application/pdf':
                # For PDFs, we would need additional processing
                # This is a placeholder - in production, you might use Google Cloud Document AI
                return f"[PDF content extraction not implemented - file: {file_id}]"
            
            elif mime_type == 'text/plain':
                # Download text files directly
                content = self.service.files().get_media(fileId=file_id).execute()
                return content.decode('utf-8')
            
            else:
                # For other file types, return metadata only
                return f"[Binary file - content extraction not available for {mime_type}]"
                
        except HttpError as e:
            print(f"Content extraction error for {file_id}: {e}")
            return None
        except Exception as e:
            print(f"Failed to extract content from {file_id}: {e}")
            return None
    
    def generate_snippet(self, content: str, query_terms: List[str], max_length: int = 200) -> str:
        """
        Generate a relevant snippet from content based on query terms
        
        Args:
            content: Full text content
            query_terms: List of terms to highlight in snippet
            max_length: Maximum length of snippet
            
        Returns:
            Generated snippet string
        """
        if not content or len(content) < max_length:
            return content[:max_length] if content else "[No content available]"
        
        # Find the best matching section
        content_lower = content.lower()
        best_score = 0
        best_start = 0
        
        # Slide a window through the content to find the most relevant section
        window_size = max_length
        step_size = window_size // 4
        
        for start in range(0, len(content) - window_size, step_size):
            window = content_lower[start:start + window_size]
            score = sum(window.count(term.lower()) for term in query_terms)
            
            if score > best_score:
                best_score = score
                best_start = start
        
        # Extract snippet around the best match
        snippet_start = max(0, best_start - 50)
        snippet_end = min(len(content), snippet_start + max_length)
        
        snippet = content[snippet_start:snippet_end]
        
        # Clean up the snippet
        snippet = re.sub(r'\s+', ' ', snippet.strip())
        
        # Add ellipsis if truncated
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def calculate_relevance_score(self, file: DriveFile, query_terms: List[str], assignment_context: Dict[str, Any]) -> float:
        """
        Calculate relevance score for a file based on multiple factors
        
        Args:
            file: DriveFile object
            query_terms: List of search terms
            assignment_context: Assignment context (title, course, etc.)
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.0
        
        # Base score from filename matching
        filename_lower = file.name.lower()
        for term in query_terms:
            if term.lower() in filename_lower:
                score += 0.3
        
        # Content matching score
        if file.content:
            content_lower = file.content.lower()
            content_matches = sum(content_lower.count(term.lower()) for term in query_terms)
            score += min(0.4, content_matches * 0.1)
        
        # Course context matching
        course_name = assignment_context.get('course', '').lower()
        if course_name and course_name in filename_lower:
            score += 0.2
        
        # File type preference (prioritize certain types)
        if file.mime_type in ['application/vnd.google-apps.document', 'application/pdf']:
            score += 0.1
        
        # Recency bonus (files modified recently get slight boost)
        # This would require parsing modified_time, simplified for now
        score += 0.05
        
        return min(1.0, score)
    
    def generate_why_useful(self, file: DriveFile, query_terms: List[str], assignment_context: Dict[str, Any]) -> str:
        """
        Generate explanation of why a file is useful for the assignment
        
        Args:
            file: DriveFile object
            query_terms: List of search terms
            assignment_context: Assignment context
            
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        # Check filename relevance
        filename_lower = file.name.lower()
        matching_terms = [term for term in query_terms if term.lower() in filename_lower]
        
        if matching_terms:
            explanations.append(f"Filename contains relevant terms: {', '.join(matching_terms)}")
        
        # Check course relevance
        course_name = assignment_context.get('course', '')
        if course_name and course_name.lower() in filename_lower:
            explanations.append(f"Specifically related to {course_name} course")
        
        # Check content relevance
        if file.content:
            content_lower = file.content.lower()
            content_terms = [term for term in query_terms if term.lower() in content_lower]
            if content_terms:
                explanations.append(f"Content includes: {', '.join(content_terms[:3])}")
        
        # File type explanation
        if file.mime_type == 'application/vnd.google-apps.document':
            explanations.append("Google Doc format - easy to read and reference")
        elif file.mime_type == 'application/pdf':
            explanations.append("PDF document - likely contains detailed information")
        
        if explanations:
            return ". ".join(explanations) + "."
        else:
            return "Contains content that may be relevant to your assignment topic."

def search_drive_for_assignment(service, assignment_data: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Main function to search Drive for assignment-relevant files
    
    Args:
        service: Authenticated Google Drive service
        assignment_data: Assignment information
        max_results: Maximum number of results to return
        
    Returns:
        List of relevant files with metadata
    """
    search_engine = DriveSearchEngine(service)
    
    # Extract search terms from assignment
    query_terms = []
    query_terms.extend(assignment_data.get('title', '').split())
    query_terms.extend(assignment_data.get('description', '').split())
    query_terms.extend(assignment_data.get('course', '').split())
    
    # Remove common stop words and clean up
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    query_terms = [term.lower().strip('.,!?;:"') for term in query_terms if term.lower() not in stop_words and len(term) > 2]
    
    # Create search query
    search_query = ' '.join(query_terms[:10])  # Limit query length
    
    # Search for files
    files = search_engine.search_files(search_query, max_results * 2)  # Get more results for filtering
    
    results = []
    for file in files[:max_results]:
        # Extract content for text-based files
        if file.mime_type in search_engine.searchable_types:
            file.content = search_engine.extract_content(file.id, file.mime_type)
        
        # Calculate relevance score
        file.relevance_score = search_engine.calculate_relevance_score(file, query_terms, assignment_data)
        
        # Generate snippet
        if file.content:
            file.snippet = search_engine.generate_snippet(file.content, query_terms)
        else:
            file.snippet = f"[{file.mime_type} file - content preview not available]"
        
        # Generate explanation
        file.why_useful = search_engine.generate_why_useful(file, query_terms, assignment_data)
        
        # Only include files with some relevance
        if file.relevance_score > 0.1:
            results.append({
                'file_id': file.id,
                'name': file.name,
                'mimeType': file.mime_type,
                'webViewLink': file.web_view_link,
                'snippet': file.snippet,
                'relevance_score': round(file.relevance_score, 2),
                'why_useful': file.why_useful
            })
    
    # Sort by relevance score
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return results

if __name__ == "__main__":
    # Test the search engine
    from drive_auth import get_drive_service
    
    service = get_drive_service()
    if service:
        test_assignment = {
            'title': 'Data101 Homework 3 - Medicare Data Analysis',
            'description': 'Analyze Medicare dataset and create visualizations',
            'course': 'Data101'
        }
        
        results = search_drive_for_assignment(service, test_assignment, max_results=5)
        print(json.dumps(results, indent=2))
    else:
        print("Failed to authenticate with Google Drive")
