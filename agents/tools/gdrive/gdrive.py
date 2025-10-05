# agents/tools/gdrive/gdrive.py

import os
import json
import re
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.baseagent import tool

# --- THE SHARED INSTANCE LOGIC ---

# 1. Define a global variable to hold our single manager instance.
_drive_manager_instance = None

def _get_drive_manager():
    """
    This function initializes the GoogleDriveManager once and returns the
    same instance on all subsequent calls. This is the singleton pattern.
    """
    global _drive_manager_instance
    if _drive_manager_instance is None:
        print("Initializing GoogleDriveManager for the first time...")
        _drive_manager_instance = GoogleDriveManager()
    return _drive_manager_instance

# --- THE MANAGER CLASS (Unchanged) ---

class GoogleDriveManager:
    """
    Google Drive manager that supports searching, folder creation,
    file management, and generating shareable links.
    """
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    ]
    SEARCHABLE_MIMETYPES = [
        "application/vnd.google-apps.document", "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.spreadsheet", "application/pdf", "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]

    def __init__(self, token_file: str = "./agents/tools/gdrive/token.json", credentials_file: str = "./agents/tools/gdrive/credentials.json"):
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.service = self._get_service()
        if not self.service:
            raise Exception("Failed to initialize Google Drive service.")

    def _get_service(self):
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try: creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}. Re-authenticating.")
                    creds = None
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Drive credentials not found at: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, "w") as token: token.write(creds.to_json())
        try:
            return build("drive", "v3", credentials=creds)
        except HttpError as e:
            print(f"Error building Drive service: {e}")
            return None

    def _extract_content(self, file_id: str, mime_type: str) -> Optional[str]:
        try:
            if "google-apps" in mime_type:
                content_bytes = self.service.files().export(fileId=file_id, mimeType="text/plain").execute()
                return content_bytes.decode("utf-8", errors="ignore") if isinstance(content_bytes, bytes) else content_bytes
            else:
                resp = self.service.files().get_media(fileId=file_id).execute()
                return resp.decode("utf-8", errors="ignore") if isinstance(resp, (bytes, bytearray)) else str(resp)
        except HttpError:
            return None

    def _calculate_relevance(self, file_name: str, content: Optional[str], query_terms: List[str]) -> float:
        score, fname = 0.0, (file_name or "").lower()
        for t in query_terms:
            if t in fname: score += 0.45
        if content:
            matches = sum(content.lower().count(t) for t in query_terms)
            score += min(0.55, matches * 0.03)
        return min(1.0, score)

    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        body = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id: body["parents"] = [parent_id]
        try:
            folder = self.service.files().create(body=body, fields="id,name,createdTime").execute()
            return {"status": "ok", "folder_id": folder.get("id"), "name": folder.get("name"), "createdTime": folder.get("createdTime")}
        except HttpError as e: return {"status": "error", "error": str(e)}

    def add_files_to_folder(self, folder_id: str, file_ids: List[str]) -> Dict[str, Any]:
        results = {"added": [], "failed": []}
        for fid in file_ids:
            try:
                meta = self.service.files().get(fileId=fid, fields="parents").execute()
                current_parents = ",".join(meta.get("parents", []))
                self.service.files().update(fileId=fid, addParents=folder_id, removeParents=current_parents, fields="id").execute()
                results["added"].append(fid)
            except HttpError as e:
                results["failed"].append({"file_id": fid, "error": str(e)})
        return {"status": "ok", "summary": results}

    def get_folder_link(self, folder_id: str, make_public: bool = True) -> Dict[str, Any]:
        try:
            meta = self.service.files().get(fileId=folder_id, fields="id,name,webViewLink").execute()
            permission_set = False
            if make_public:
                try:
                    self.service.permissions().create(fileId=folder_id, body={"type": "anyone", "role": "reader"}, fields="id").execute()
                    permission_set = True
                except HttpError as e_perm:
                    print(f"Permission creation failed: {e_perm}")
            return {"status": "ok", "folder_id": folder_id, "webViewLink": meta.get("webViewLink"), "permission_set": permission_set}
        except HttpError as e: return {"status": "error", "error": str(e)}

    def search_files_for_assignment(self, assignment_data: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
        query_text = f"{assignment_data.get('title','')} {assignment_data.get('course_name','')}"
        stop_words = {"the", "a", "an", "and", "in", "on", "of", "for", "with", "to", "by"}
        terms = [t for t in re.split(r"\W+", query_text.lower()) if t and t not in stop_words]
        if not terms: return []

        q = " or ".join([f"fullText contains '{t}'" for t in terms])
        try:
            resp = self.service.files().list(q=f"({q}) and trashed=false", pageSize=max_results * 2,
                                            fields="files(id,name,mimeType,webViewLink,modifiedTime)").execute()
        except HttpError as e: return [{"status": "error", "error": str(e)}]

        results = []
        for f in resp.get("files", []):
            content = self._extract_content(f["id"], f.get("mimeType")) if f.get("mimeType") in self.SEARCHABLE_MIMETYPES else None
            score = self._calculate_relevance(f.get("name", ""), content, terms)
            if score > 0.15:
                snippet = "No text snippet available." # Simplified snippet logic
                results.append({"file_id": f["id"], "name": f.get("name"), "webViewLink": f.get("webViewLink"),
                                "relevance_score": round(score, 3), "snippet": snippet})
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:max_results]


# --- Tools (Now using the shared instance) ---
@tool
def tool_create_drive_folder(folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a folder in Google Drive.
    """
    try:
        mgr = _get_drive_manager()
        return mgr.create_folder(folder_name, parent_id)
    except Exception as e:
        return {"status": "error", "error": f"Tool-level error: {e}"}

@tool
def tool_add_files_to_folder(folder_id: str, file_ids: List[str]) -> Dict[str, Any]:
    """
    Adds files to a specified folder.
    """
    try:
        mgr = _get_drive_manager()
        return mgr.add_files_to_folder(folder_id, file_ids)
    except Exception as e:
        return {"status": "error", "error": f"Tool-level error: {e}"}

@tool
def tool_get_folder_link(folder_id: str, make_public: bool = True) -> Dict[str, Any]:
    """
    Gets a shareable link for a folder.
    """
    try:
        mgr = _get_drive_manager()
        return mgr.get_folder_link(folder_id, make_public)
    except Exception as e:
        return {"status": "error", "error": f"Tool-level error: {e}"}

@tool
def tool_search_drive_for_assignment(assignment_title: str, course_name: str, max_results: int = 5) -> Any:
    """
    Searches Drive for files relevant to a given assignment.
    """
    try:
        mgr = _get_drive_manager()
        return mgr.search_files_for_assignment({"title": assignment_title, "course_name": course_name}, max_results)
    except Exception as e:
        return {"status": "error", "error": f"Tool-level error: {e}"}