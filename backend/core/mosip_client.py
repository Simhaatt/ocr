import requests
import json
import logging
from typing import Dict, Optional, Any
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)

class MOSIPPreRegistrationRequest(BaseModel):
    """Pydantic model for MOSIP pre-registration"""
    langCode: str = "eng"
    demographicDetails: Dict[str, Any]

class MOSIPClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "MOSIP-OCR-Integration/1.0.0"
        }
        logger.info(f"MOSIP Client initialized for {base_url}")
    
    def map_to_mosip_schema(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map OCR extracted data to MOSIP schema"""
        # This mapping should be customized based on your OCR output
        field_mapping = {
            "Name": "fullName",
            "FirstName": "firstName",
            "LastName": "lastName",
            "FullName": "fullName",
            "Age": "age",
            "DateOfBirth": "dateOfBirth",
            "DOB": "dateOfBirth",
            "BirthDate": "dateOfBirth",
            "Gender": "gender",
            "Sex": "gender",
            "Address": "addressLine1",
            "AddressLine1": "addressLine1",
            "AddressLine2": "addressLine2",
            "Street": "addressLine1",
            "City": "city",
            "State": "region",
            "Province": "region",
            "PinCode": "postalCode",
            "PostalCode": "postalCode",
            "ZipCode": "postalCode",
            "Phone": "phone",
            "PhoneNumber": "phone",
            "Mobile": "phone",
            "Email": "email",
            "EmailId": "email",
            "Country": "country",
            "Nationality": "country"
        }
        
        mosip_data = {}
        for ocr_key, value in extracted_data.items():
            if ocr_key in field_mapping:
                mosip_key = field_mapping[ocr_key]
                mosip_data[mosip_key] = value
            else:
                # Try case-insensitive match
                for map_key, map_value in field_mapping.items():
                    if map_key.lower() == ocr_key.lower():
                        mosip_data[map_value] = value
                        break
        
        return mosip_data
    
    def create_pre_registration(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create MOSIP pre-registration application"""
        try:
            url = f"{self.base_url}/preregistration/v1/applications"
            
            # Map to MOSIP schema
            mosip_data = self.map_to_mosip_schema(extracted_data)
            
            # Build MOSIP payload according to their API spec
            payload = {
                "id": "mosip.pre-registration",
                "version": "1.0",
                "requesttime": self._get_timestamp(),
                "request": {
                    "langCode": "eng",
                    "demographicDetails": {
                        "identity": self._build_identity_object(mosip_data)
                    }
                }
            }
            
            logger.debug(f"Sending pre-registration request: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=self.headers, 
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"MOSIP pre-registration created: {result.get('response', {}).get('preRegistrationId', 'Unknown')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"MOSIP API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"MOSIP API call failed: {str(e)}")
    
    def _build_identity_object(self, mosip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the identity object for MOSIP payload"""
        identity = {}
        
        # Name handling
        if "fullName" in mosip_data:
            identity["fullName"] = [{
                "language": "eng",
                "value": str(mosip_data["fullName"])
            }]
        
        # Date of Birth
        if "dateOfBirth" in mosip_data:
            identity["dateOfBirth"] = str(mosip_data["dateOfBirth"])
        
        # Gender
        if "gender" in mosip_data:
            gender_value = str(mosip_data["gender"]).upper()
            if gender_value in ["MALE", "FEMALE", "OTHER"]:
                identity["gender"] = [{
                    "language": "eng",
                    "value": gender_value
                }]
        
        # Address components
        address_fields = ["addressLine1", "addressLine2", "city", "region", "country"]
        for field in address_fields:
            if field in mosip_data:
                identity[field] = [{
                    "language": "eng",
                    "value": str(mosip_data[field])
                }]
        
        # Postal code
        if "postalCode" in mosip_data:
            identity["postalCode"] = str(mosip_data["postalCode"])
        
        # Contact info
        if "phone" in mosip_data:
            identity["phone"] = str(mosip_data["phone"])
        
        if "email" in mosip_data:
            identity["email"] = str(mosip_data["email"])
        
        return identity
    
    def upload_document(self, pre_registration_id: str, document_path: str, 
                       document_type: str = "POI") -> Dict[str, Any]:
        """Upload document to MOSIP pre-registration"""
        try:
            url = f"{self.base_url}/preregistration/v1/documents/{pre_registration_id}"
            
            # Prepare multipart form data
            with open(document_path, 'rb') as file:
                files = {'file': (os.path.basename(document_path), file, 'application/octet-stream')}
                
                data = {
                    "docCatCode": document_type,
                    "docTypCode": document_type,
                    "langCode": "eng"
                }
                
                # Remove Content-Type header for multipart upload
                headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
                
                logger.info(f"Uploading document to MOSIP for pre-registration: {pre_registration_id}")
                response = requests.post(
                    url, 
                    files=files, 
                    data=data, 
                    headers=headers, 
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Document uploaded successfully")
                return result
                
        except Exception as e:
            logger.error(f"Document upload failed: {str(e)}")
            raise
    
    def get_application_status(self, pre_registration_id: str) -> Dict[str, Any]:
        """Check pre-registration application status"""
        try:
            url = f"{self.base_url}/preregistration/v1/applications/{pre_registration_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get application status: {str(e)}")
            raise
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
