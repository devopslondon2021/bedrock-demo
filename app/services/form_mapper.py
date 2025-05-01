import pandas as pd
import boto3
from typing import Dict, Any
import logging
from app.core.config import get_settings
import io

logger = logging.getLogger(__name__)

class FormMapper:
    def __init__(self):
        self.settings = get_settings()
        self.s3_client = boto3.client('s3',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_region
        )
        self.bucket_name = "demo-bucket-986123"
        self.forms_prefix = "msforms/"
        
        # Define form mappings for different column names
        self.field_mappings = {
            'name': ['Full Name', 'Name', 'Customer Name'],
            'first_name': ['First Name', 'FirstName', 'Given Name'],
            'middle_name': ['Middle Name', 'MiddleName'],
            'last_name': ['Last Name', 'LastName', 'Surname'],
            'date_of_birth': ['DOB', 'Date of Birth', 'Birth Date'],
            'post_code': ['Post Code', 'Postcode', 'Pin Code', 'ZIP', 'Postal Code'],
            'car_make': ['Car Make', 'Make', 'Vehicle Make', 'Car Make'],
            'car_model': ['Car Model', 'Model', 'Vehicle Model', 'Car Model']
        }
        
        # Initialize Excel files if they don't exist
        self._initialize_excel_files()
        
    def _initialize_excel_files(self):
        """Create Excel files if they don't exist"""
        try:
            # Check if files exist
            for file_name in ['MSForm1.xlsx', 'MSForm2.xlsx']:
                try:
                    self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=f"{self.forms_prefix}{file_name}"
                    )
                except self.s3_client.exceptions.ClientError:
                    # File doesn't exist, create it
                    logger.info(f"Creating new Excel file: {file_name}")
                    # Create empty DataFrame with columns
                    columns = [
                        'Full Name', 'First Name', 'Middle Name', 'Last Name',
                        'Date of Birth', 'Post Code', 'Car Make', 'Car Model'
                    ]
                    df = pd.DataFrame(columns=columns)
                    buffer = io.BytesIO()
                    df.to_excel(buffer, index=False)
                    buffer.seek(0)
                    
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=f"{self.forms_prefix}{file_name}",
                        Body=buffer.getvalue()
                    )
        except Exception as e:
            logger.error(f"Error initializing Excel files: {e}")
            
    def _get_excel_from_s3(self, file_name: str) -> pd.DataFrame:
        """Fetch Excel file from S3 and return as DataFrame"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=f"{self.forms_prefix}{file_name}"
            )
            buffer = io.BytesIO(response['Body'].read())
            buffer.seek(0)  # Reset buffer position
            try:
                df = pd.read_excel(buffer)
                return df
            except Exception as excel_error:
                logger.error(f"Error reading Excel content: {excel_error}")
                # If file is corrupted or empty, create new DataFrame
                columns = [
                    'Full Name', 'First Name', 'Middle Name', 'Last Name',
                    'Date of Birth', 'Post Code', 'Car Make', 'Car Model'
                ]
                return pd.DataFrame(columns=columns)
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Excel file {file_name} not found, creating new one")
            columns = [
                'Full Name', 'First Name', 'Middle Name', 'Last Name',
                'Date of Birth', 'Post Code', 'Car Make', 'Car Model'
            ]
            return pd.DataFrame(columns=columns)
        except Exception as e:
            logger.error(f"Error accessing Excel from S3: {e}")
            raise
            
    def _save_excel_to_s3(self, df: pd.DataFrame, file_name: str):
        """Save DataFrame back to S3 as Excel"""
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"{self.forms_prefix}{file_name}",
                Body=buffer.getvalue(),
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            logger.info(f"Successfully saved {file_name} to S3")
        except Exception as e:
            logger.error(f"Error saving Excel to S3: {e}")
            raise
            
    def _find_matching_column(self, columns: list, field_type: str) -> str:
        """Find the matching column name from the Excel file"""
        possible_names = self.field_mappings.get(field_type, [])
        for name in possible_names:
            if name in columns:
                return name
        return None
            
    def _prepare_row_data(self, analysis: Dict[str, Any], columns: list) -> Dict[str, Any]:
        """Prepare row data according to form columns"""
        row_data = {}
        
        # Handle name fields
        if self._find_matching_column(columns, 'name'):
            # Combine names if form has single name field
            name_parts = [
                analysis['customer'].get('first_name', ''),
                analysis['customer'].get('middle_name', ''),
                analysis['customer'].get('last_name', '')
            ]
            row_data[self._find_matching_column(columns, 'name')] = ' '.join(filter(None, name_parts))
        else:
            # Handle separate name fields
            for name_type in ['first_name', 'middle_name', 'last_name']:
                col = self._find_matching_column(columns, name_type)
                if col:
                    row_data[col] = analysis['customer'].get(name_type.replace('_', ''), '')
        
        # Handle other fields
        field_mapping = {
            'date_of_birth': analysis.get('date_of_birth', ''),
            'post_code': analysis.get('post_code', ''),
            'car_make': analysis['vehicle'].get('make', ''),
            'car_model': analysis['vehicle'].get('model', '')  # This should already contain "Model X"
        }
        
        for field, value in field_mapping.items():
            col = self._find_matching_column(columns, field)
            if col:
                if field == 'car_model' and not value:
                    # Special handling for car model if it's empty
                    make = analysis['vehicle'].get('make', '').lower()
                    if make == 'tesla' and 'model' in analysis['vehicle']:
                        # For Tesla, the model often includes "Model" in the name
                        value = analysis['vehicle']['model']
                row_data[col] = value
                
        logger.info(f"Prepared row data: {row_data}")  # Add logging to see what's being prepared
        return row_data
        
    def submit_to_forms(self, analysis: Dict[str, Any]) -> Dict[str, bool]:
        """Submit data to appropriate MS Form based on car make"""
        results = {'MSForm1': False, 'MSForm2': False}
        car_make = analysis['vehicle'].get('make', '').lower()
        
        try:
            if car_make == 'bmw':
                # Handle BMW submission to MSForm1
                df = self._get_excel_from_s3('MSForm1.xlsx')
                row_data = self._prepare_row_data(analysis, df.columns.tolist())
                df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
                self._save_excel_to_s3(df, 'MSForm1.xlsx')
                results['MSForm1'] = True
                logger.info("Successfully submitted to MSForm1 (BMW)")
                
            elif car_make == 'tesla':
                # Handle Tesla submission to MSForm2
                df = self._get_excel_from_s3('MSForm2.xlsx')
                row_data = self._prepare_row_data(analysis, df.columns.tolist())
                df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
                self._save_excel_to_s3(df, 'MSForm2.xlsx')
                results['MSForm2'] = True
                logger.info("Successfully submitted to MSForm2 (Tesla)")
            
            else:
                logger.warning(f"Car make '{car_make}' doesn't match any form criteria")
                
        except Exception as e:
            logger.error(f"Error submitting to MS Forms: {e}")
            
        return results 