from typing import Dict, Any
import os
import gspread
from google.oauth2.service_account import Credentials
from ..core.logger import logger
from app.core.config import get_settings

class GoogleSheetsService:
    def __init__(self):
        self.settings = get_settings()
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file',
        ]
        
        creds = Credentials.from_service_account_file(
            self.settings.google_service_account_file, 
            scopes=scope
        )
        
        self.gc = gspread.authorize(creds)
        self.spreadsheet = self.gc.open_by_key(self.settings.google_spreadsheet_id)
        self.worksheet = self.spreadsheet.sheet1  # Use Sheet1 instead of custom worksheet
        
    def submit_response(self, analysis):
        try:
            # Prepare row data
            row_data = [
                analysis['customer']['first_name'],
                analysis['customer']['middle_name'] or 'Not provided',
                analysis['customer']['last_name'],
                analysis['date_of_birth'],
                analysis['vehicle']['make'],
                analysis['vehicle']['model'],
                analysis['post_code']
            ]
            
            # Append the row
            self.worksheet.append_row(row_data)
            return True
            
        except Exception as e:
            print(f"Error submitting to Google Sheets: {e}")
            return False 