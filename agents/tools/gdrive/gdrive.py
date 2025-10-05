import os
import json
import re
import datetime as dt
from typing import List, Dict, Any, Optional, Tuple

from agents.baseagent import *

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDriveManager:
    """Manages Google Drive authentication, searching, and content analysis."""

    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]
    
    # File types that can be searched for content
    SEARCHABLE_MIMETYPES = [
        'application/vnd.google-apps.document',
        'application/vnd.google-apps.presentation',
        'application/vnd.google-apps.spreadsheet',
        'application/pdf',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ]

    def __init__(self):
        """Initializes the manager and authenticates with the Google Drive API."""
        self.service = self._get_service()
        if not self.service:
            raise Exception("Failed to authenticate and initialize Google Drive service.")

    def _get_service(self) -> Optional[Any]:
        """Handles OAuth2 flow to get an authorized Google Drive service object."""
        creds = None
        # NOTE: Adjust these file paths if your project structure is different.
        token_file = './agents/tools/drive/token.json'
        credentials_file = './agents/tools/drive/credentials.json'

        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}. Re-authenticating.")
                    creds = None # Force re-authentication
            
            if not creds:
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(f"Google Drive credentials file not found at: {credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)

            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            return build('drive', 'v3', credentials=creds)
        except HttpError as e:
            print(f"An error occurred building the Google Drive service: {e}")
            return None

    def _extract_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """Extracts text content from a Drive file if possible."""
        try:
            # Export Google Workspace files as plain text
            if 'google-apps' in mime_type:
                content_bytes = self.service.files().export(fileId=file_id, mimeType='text/plain').execute()
                return content_bytes.decode('utf-8')
            # Download text-based files directly
            elif mime_type == 'text/plain' or mime_type == 'application/pdf':
                content_bytes = self.service.files().get_media(fileId=file_id).execute()
                # For PDFs, this gets the raw bytes. Actual text extraction would need a library
                # like PyMuPDF, but for relevance, we can search the raw text.
                # A simple decode is used here, which may not be perfect for all PDFs.
                return content_bytes.decode('utf-8', errors='ignore')
            return None
        except HttpError as e:
            # Common for files that don't support export or media download
            print(f"Could not extract content from {file_id} (MIME: {mime_type}): {e}")
            return None

    def _calculate_relevance(self, file_name: str, content: Optional[str], query_terms: List[str]) -> float:
        """Calculates a relevance score based on term matching."""
        score = 0.0
        name_lower = file_name.lower()
        
        # Strong weight for matching terms in the filename
        for term in query_terms:
            if term in name_lower:
                score += 0.4
        
        # Medium weight for matching terms in the content
        if content:
            content_lower = content.lower()
            content_matches = sum(content_lower.count(term) for term in query_terms)
            score += min(0.6, content_matches * 0.05) # Add score based on frequency
            
        return min(1.0, score)

    def search_files_for_assignment(self, assignment_data: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches Drive for files relevant to an assignment, scores them, and returns the best matches.
        """
        # 1. Create search query from assignment details
        query_text = f"{assignment_data.get('title', '')} {assignment_data.get('course_name', '')}"
        stop_words = {'the', 'a', 'an', 'and', 'in', 'on', 'of', 'for', 'with'}
        query_terms = [term for term in re.split(r'\W+', query_text.lower()) if term and term not in stop_words]
        
        search_query_str = ' or '.join(f"fullText contains '{term}'" for term in query_terms)
        search_query_str = f"({search_query_str}) and trashed=false"

        # 2. Execute search against the Drive API
        try:
            response = self.service.files().list(
                q=search_query_str,
                pageSize=max_results * 2, # Fetch more to allow for better scoring
                fields="files(id, name, mimeType, webViewLink, modifiedTime, parents)",
                orderBy="modifiedTime desc"
            ).execute()
            files = response.get('files', [])
        except HttpError as e:
            return f"An error occurred during Drive search: {e}"

        # 3. Process and score results
        results = []
        for file in files:
            content = None
            if file.get('mimeType') in self.SEARCHABLE_MIMETYPES:
                content = self._extract_content(file['id'], file['mimeType'])
            
            relevance_score = self._calculate_relevance(file['name'], content, query_terms)

            # Only include results with a meaningful relevance score
            if relevance_score > 0.2:
                snippet = ""
                if content:
                    # Generate a simple snippet
                    first_match_pos = -1
                    for term in query_terms:
                        pos = content.lower().find(term)
                        if pos != -1:
                            first_match_pos = pos
                            break
                    start = max(0, first_match_pos - 50)
                    snippet = content[start : start + 250].strip()
                    if start > 0: snippet = "..." + snippet
                    snippet += "..."

                results.append({
                    'file_id': file['id'],
                    'name': file['name'],
                    'mimeType': file['mimeType'],
                    'webViewLink': file['webViewLink'],
                    'relevance_score': round(relevance_score, 2),
                    'snippet': snippet or "No text snippet available."
                })
        
        # 4. Sort by score and return the top results
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:max_results]


# --- Agent Tool ---

@tool
def tool_search_drive_for_assignment(assignment_title: str, course_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Searches the user's Google Drive for files relevant to a specific assignment.
    It returns a list of the most relevant files, scored and sorted by relevance.
    
    Args:
        assignment_title (str): The title of the assignment (e.g., "History of Rome Essay").
        course_name (str): The name of the course (e.g., "HIST 101").
        max_results (int): The maximum number of relevant files to return. Defaults to 5.
    
    Returns:
        A list of dictionaries, each representing a relevant file with its name, link, relevance score, and a content snippet.
    """
    try:
        manager = GoogleDriveManager()
        assignment_data = {
            "title": assignment_title,
            "course_name": course_name
        }
        return manager.search_files_for_assignment(assignment_data, max_results)
    except Exception as e:
        return f"An error occurred while searching Google Drive: {e}"

if __name__ == '__main__':
    # Example usage of the tool
    print("--- Searching Google Drive for relevant assignment files ---")
    
    # Define a sample assignment to search for
    example_assignment_title = "Data101 Medicare Data Analysis"
    example_course_name = "Data101"
    
    # Use the tool to get results
    relevant_files = tool_search_drive_for_assignment(
        assignment_title=example_assignment_title,
        course_name=example_course_name,
        max_results=5
    )
    
    print(f"Found the following relevant files for '{example_assignment_title}':")
    print(json.dumps(relevant_files, indent=2))
