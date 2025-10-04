"""
Google Drive Authentication Handler
Handles OAuth2 and Service Account authentication for Google Drive API
"""

import os
import json
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

class DriveAuthHandler:
    """Handles Google Drive API authentication using OAuth2 or Service Account"""
    
    # Drive API scopes for read-only access
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]
    
    def __init__(self, auth_type: str = "oauth2"):
        """
        Initialize Drive authentication handler
        
        Args:
            auth_type: "oauth2" for user authentication, "service_account" for server-to-server
        """
        self.auth_type = auth_type
        self.service = None
        self.credentials = None
        
    def authenticate_oauth2(self, credentials_file: str = None, token_file: str = None) -> bool:
        """
        Authenticate using OAuth2 flow for user access
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store/load token file
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Default paths
            if not credentials_file:
                credentials_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', './agents/tools/drive/credentials.json')
            if not token_file:
                token_file = os.getenv('GOOGLE_DRIVE_TOKEN_FILE', './agents/tools/drive/token.json')
                
            creds = None
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
            
            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_file):
                        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            print(f"OAuth2 authentication failed: {e}")
            return False
    
    def authenticate_service_account(self, service_account_file: str = None, delegated_user: str = None) -> bool:
        """
        Authenticate using Service Account with optional domain-wide delegation
        
        Args:
            service_account_file: Path to service account JSON file
            delegated_user: Email of user to impersonate (for domain-wide delegation)
            
        Returns:
            bool: True if authentication successful
        """
        try:
            if not service_account_file:
                service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
            
            if not service_account_file or not os.path.exists(service_account_file):
                raise FileNotFoundError("Service account file not found")
            
            if delegated_user:
                # Domain-wide delegation
                creds = ServiceAccountCredentials.from_service_account_file(
                    service_account_file, scopes=self.SCOPES, subject=delegated_user
                )
            else:
                # Regular service account
                creds = ServiceAccountCredentials.from_service_account_file(
                    service_account_file, scopes=self.SCOPES
                )
            
            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            print(f"Service account authentication failed: {e}")
            return False
    
    def authenticate(self) -> bool:
        """Main authentication method - tries OAuth2 first, then service account"""
        if self.auth_type == "oauth2":
            return self.authenticate_oauth2()
        elif self.auth_type == "service_account":
            return self.authenticate_service_account()
        else:
            # Auto-detect: try OAuth2 first, fallback to service account
            if self.authenticate_oauth2():
                return True
            return self.authenticate_service_account()
    
    def get_service(self):
        """Get authenticated Drive service object"""
        if not self.service:
            if not self.authenticate():
                raise Exception("Failed to authenticate with Google Drive API")
        return self.service
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Drive API connection and return user info"""
        try:
            service = self.get_service()
            
            # Get user info
            about = service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            
            return {
                "success": True,
                "user_email": user_info.get('emailAddress', 'Unknown'),
                "user_name": user_info.get('displayName', 'Unknown'),
                "auth_type": self.auth_type
            }
            
        except HttpError as e:
            return {
                "success": False,
                "error": f"Drive API error: {e}",
                "error_code": e.resp.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {e}"
            }

def get_drive_service(auth_type: str = "oauth2") -> Optional[Any]:
    """
    Convenience function to get authenticated Drive service
    
    Args:
        auth_type: Authentication method to use
        
    Returns:
        Google Drive service object or None if authentication fails
    """
    handler = DriveAuthHandler(auth_type)
    try:
        return handler.get_service()
    except Exception as e:
        print(f"Failed to get Drive service: {e}")
        return None

if __name__ == "__main__":
    # Test authentication
    handler = DriveAuthHandler()
    result = handler.test_connection()
    print(json.dumps(result, indent=2))
