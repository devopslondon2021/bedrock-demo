import pandas as pd
import boto3
from typing import Dict, Any, Tuple
import io
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ExcelService:
    # Define the exact column names as they appear in the source file
    SOURCE_COLUMNS = [
        'First Name',
        'Middle Name',
        'Last Name',
        'DOB',
        'Car Make',
        'Car Model',
        'Post Code'
    ]

    # Define column names for MSForm1 (BMW)
    MSFORM1_COLUMNS = [
        'Full Name',
        'DOB',
        'Car Make',
        'Car Model',
        'Pin Code'
    ]

    # Define column names for MSForm2 (Tesla)
    MSFORM2_COLUMNS = [
        'Name',
        'DOB',
        'Car Make',
        'Car Model',
        'Pin Code'
    ]

    def __init__(self):
        self.settings = get_settings()
        self.s3_client = boto3.client('s3',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_region
        )
        
    def _get_excel_from_s3(self, key: str, columns: list) -> pd.DataFrame:
        """Fetch Excel file from S3 and return as DataFrame"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.settings.s3_bucket,
                Key=key
            )
            buffer = io.BytesIO(response['Body'].read())
            buffer.seek(0)  # Reset buffer position
            try:
                df = pd.read_excel(buffer)
                return df
            except Exception as excel_error:
                logger.error(f"Error reading Excel content from {key}: {excel_error}")
                # Create new DataFrame with correct columns if file is corrupted
                return pd.DataFrame(columns=columns)
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Excel file not found at {key}, creating new one with correct columns")
            return pd.DataFrame(columns=columns)
            
    def _save_excel_to_s3(self, df: pd.DataFrame, key: str) -> bool:
        """Save DataFrame back to S3 as Excel"""
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)
            
            self.s3_client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            logger.info(f"Successfully saved Excel file to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving Excel to S3 {key}: {e}")
            return False

    def _clean_car_model(self, model: str) -> str:
        """Clean car model name to remove prefixes"""
        # Remove 'Model ' prefix if present
        return model.replace('Model ', '') if 'Model ' in model else model

    def _format_for_msform1(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data for MSForm1 (BMW) format"""
        # Combine names for Full Name
        full_name = f"{row_data['First Name']} {row_data['Middle Name']} {row_data['Last Name']}".replace('Not provided', '').strip()
        return {
            'Full Name': full_name,
            'DOB': row_data['DOB'],
            'Car Make': row_data['Car Make'],
            'Car Model': self._clean_car_model(row_data['Car Model']),
            'Pin Code': row_data['Post Code']
        }

    def _format_for_msform2(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data for MSForm2 (Tesla) format"""
        # Combine names for Name
        name = f"{row_data['First Name']} {row_data['Middle Name']} {row_data['Last Name']}".replace('Not provided', '').strip()
        return {
            'Name': name,
            'DOB': row_data['DOB'],
            'Car Make': row_data['Car Make'],
            'Car Model': self._clean_car_model(row_data['Car Model']),
            'Pin Code': row_data['Post Code']
        }

    def _copy_to_msforms(self, row_data: Dict[str, Any], car_make: str) -> Tuple[bool, bool]:
        """Copy data to appropriate MS Form based on car make"""
        msform1_success = False
        msform2_success = False
        
        try:
            if car_make.lower() == 'bmw':
                # Format data for MSForm1 and save
                msform1_key = 'destination/msforms/MSForm1.xlsx'
                df_msform1 = self._get_excel_from_s3(msform1_key, self.MSFORM1_COLUMNS)
                formatted_data = self._format_for_msform1(row_data)
                df_msform1 = pd.concat([df_msform1, pd.DataFrame([formatted_data])], ignore_index=True)
                msform1_success = self._save_excel_to_s3(df_msform1, msform1_key)
                logger.info("Data copied to MSForm1.xlsx (BMW)")
                
            elif car_make.lower() == 'tesla':
                # Format data for MSForm2 and save
                msform2_key = 'destination/msforms/MSForm2.xlsx'
                df_msform2 = self._get_excel_from_s3(msform2_key, self.MSFORM2_COLUMNS)
                formatted_data = self._format_for_msform2(row_data)
                df_msform2 = pd.concat([df_msform2, pd.DataFrame([formatted_data])], ignore_index=True)
                msform2_success = self._save_excel_to_s3(df_msform2, msform2_key)
                logger.info("Data copied to MSForm2.xlsx (Tesla)")
                
        except Exception as e:
            logger.error(f"Error copying to MS Forms: {e}")
            
        return msform1_success, msform2_success
            
    def submit_response(self, analysis: Dict[str, Any]) -> Dict[str, bool]:
        """Submit analysis data to Excel files in S3"""
        try:
            # Get existing Excel file or create new one with correct columns
            source_df = self._get_excel_from_s3(self.settings.s3_excel_file, self.SOURCE_COLUMNS)
            
            # Prepare row data with exact column names
            row_data = {
                'First Name': analysis['customer']['first_name'],
                'Middle Name': analysis['customer'].get('middle_name', 'Not provided'),
                'Last Name': analysis['customer']['last_name'],
                'DOB': analysis['date_of_birth'],
                'Car Make': analysis['vehicle']['make'],
                'Car Model': analysis['vehicle']['model'],
                'Post Code': analysis['post_code']
            }
            
            # Append new row to source file
            source_df = pd.concat([source_df, pd.DataFrame([row_data])], ignore_index=True)
            source_success = self._save_excel_to_s3(source_df, self.settings.s3_excel_file)
            
            # Copy to MS Forms based on car make
            msform1_success, msform2_success = self._copy_to_msforms(row_data, analysis['vehicle']['make'])
            
            return {
                'source_success': source_success,
                'msform1_success': msform1_success,
                'msform2_success': msform2_success
            }
            
        except Exception as e:
            logger.error(f"Error submitting to Excel: {e}")
            return {
                'source_success': False,
                'msform1_success': False,
                'msform2_success': False
            } 