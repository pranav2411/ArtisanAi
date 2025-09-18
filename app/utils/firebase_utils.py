"""
Firebase Utilities

This module provides utility functions for Firebase operations with proper error handling.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
from firebase_admin.auth import UserRecord
from firebase_admin.exceptions import FirebaseError
from google.cloud.firestore_v1 import DocumentSnapshot
from werkzeug.exceptions import BadRequest, Forbidden, InternalServerError, NotFound, Unauthorized

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')

class FirebaseServiceError(Exception):
    """Base exception for Firebase service errors."""
    def __init__(self, message: str, code: int = 500, details: Any = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)

class FirebaseAuthError(FirebaseServiceError):
    """Raised when there's an authentication/authorization error with Firebase."""
    def __init__(self, message: str, code: int = 401, details: Any = None):
        super().__init__(message, code, details)

class FirebaseNotFoundError(FirebaseServiceError):
    """Raised when a requested resource is not found in Firebase."""
    def __init__(self, message: str, code: int = 404, details: Any = None):
        super().__init__(message, code, details)

class FirebaseValidationError(FirebaseServiceError):
    """Raised when there's a validation error with Firebase data."""
    def __init__(self, message: str, code: int = 400, details: Any = None):
        super().__init__(message, code, details)

def handle_firebase_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle Firebase errors and convert them to appropriate exceptions.
    
    Args:
        func: The function to wrap with error handling.
        
    Returns:
        The wrapped function with error handling.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except auth.UserNotFoundError as e:
            logger.warning(f"User not found: {str(e)}")
            raise FirebaseNotFoundError("User not found", 404) from e
        except auth.EmailAlreadyExistsError as e:
            logger.warning(f"Email already exists: {str(e)}")
            raise FirebaseValidationError("Email already in use", 400) from e
        except auth.PhoneNumberAlreadyExistsError as e:
            logger.warning(f"Phone number already exists: {str(e)}")
            raise FirebaseValidationError("Phone number already in use", 400) from e
        except auth.UidAlreadyExistsError as e:
            logger.warning(f"User ID already exists: {str(e)}")
            raise FirebaseValidationError("User ID already exists", 400) from e
        except auth.InvalidEmailError as e:
            logger.warning(f"Invalid email: {str(e)}")
            raise FirebaseValidationError("Invalid email address", 400) from e
        except auth.WeakPasswordError as e:
            logger.warning(f"Weak password: {str(e)}")
            raise FirebaseValidationError("Password is too weak", 400) from e
        except auth.InvalidPasswordError as e:
            logger.warning(f"Invalid password: {str(e)}")
            raise FirebaseValidationError("Invalid password", 400) from e
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Invalid ID token: {str(e)}")
            raise FirebaseAuthError("Invalid authentication token", 401) from e
        except auth.ExpiredIdTokenError as e:
            logger.warning(f"Expired ID token: {str(e)}")
            raise FirebaseAuthError("Authentication token has expired", 401) from e
        except auth.RevokedIdTokenError as e:
            logger.warning(f"Revoked ID token: {str(e)}")
            raise FirebaseAuthError("Authentication token has been revoked", 401) from e
        except auth.UserDisabledError as e:
            logger.warning(f"User account is disabled: {str(e)}")
            raise FirebaseAuthError("User account is disabled", 403) from e
        except auth.InvalidCredentialError as e:
            logger.error(f"Invalid Firebase credentials: {str(e)}")
            raise FirebaseAuthError("Invalid authentication credentials", 401) from e
        except ValueError as e:
            logger.error(f"Value error in Firebase operation: {str(e)}")
            raise FirebaseValidationError(f"Invalid input data: {str(e)}", 400) from e
        except FirebaseError as e:
            logger.error(f"Firebase error: {str(e)}")
            raise FirebaseServiceError("An error occurred with the authentication service", 500) from e
        except Exception as e:
            logger.exception("Unexpected error in Firebase operation")
            raise FirebaseServiceError("An unexpected error occurred", 500) from e
    return wrapper

class FirebaseService:
    """Service class for Firebase operations with proper error handling."""
    
    def __init__(self, app=None):
        """Initialize the Firebase service."""
        self.app = app
        self._auth = None
        self._db = None
        self._storage = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app) -> None:
        """Initialize the Firebase app with the given Flask app."""
        self.app = app
        
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Initialize with service account credentials
                cred = credentials.Certificate(app.config['GOOGLE_APPLICATION_CREDENTIALS'])
                firebase_admin.initialize_app(cred, {
                    'storageBucket': app.config.get('FIREBASE_STORAGE_BUCKET', '')
                })
            
            # Initialize services
            self._auth = auth.Client()
            self._db = firestore.client()
            self._storage = storage.bucket()
            
        except Exception as e:
            logger.critical(f"Failed to initialize Firebase: {str(e)}")
            raise RuntimeError("Failed to initialize Firebase services") from e
    
    @property
    def auth(self):
        """Get the Firebase Auth client."""
        if self._auth is None:
            raise RuntimeError("Firebase Auth not initialized. Call init_app first.")
        return self._auth
    
    @property
    def db(self):
        """Get the Firestore client."""
        if self._db is None:
            raise RuntimeError("Firestore not initialized. Call init_app first.")
        return self._db
    
    @property
    def storage_bucket(self):
        """Get the Cloud Storage bucket."""
        if self._storage is None:
            raise RuntimeError("Cloud Storage not initialized. Call init_app first.")
        return self._storage
    
    # Authentication Methods
    
    @handle_firebase_errors
    def get_user(self, uid: str) -> UserRecord:
        """Get a user by UID."""
        return self.auth.get_user(uid)
    
    @handle_firebase_errors
    def get_user_by_email(self, email: str) -> UserRecord:
        """Get a user by email."""
        return self.auth.get_user_by_email(email)
    
    @handle_firebase_errors
    def create_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        photo_url: Optional[str] = None,
        disabled: bool = False,
        email_verified: bool = False
    ) -> UserRecord:
        """Create a new user."""
        user_args = {
            'email': email,
            'password': password,
            'display_name': display_name,
            'phone_number': phone_number,
            'photo_url': photo_url,
            'disabled': disabled,
            'email_verified': email_verified
        }
        # Remove None values
        user_args = {k: v for k, v in user_args.items() if v is not None}
        return self.auth.create_user(**user_args)
    
    @handle_firebase_errors
    def update_user(
        self,
        uid: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        disabled: Optional[bool] = None,
        email_verified: Optional[bool] = None
    ) -> UserRecord:
        """Update an existing user."""
        user_args = {
            'uid': uid,
            'email': email,
            'password': password,
            'display_name': display_name,
            'photo_url': photo_url,
            'disabled': disabled,
            'email_verified': email_verified
        }
        # Remove None values
        user_args = {k: v for k, v in user_args.items() if v is not None}
        return self.auth.update_user(**user_args)
    
    @handle_firebase_errors
    def delete_user(self, uid: str) -> None:
        """Delete a user."""
        self.auth.delete_user(uid)
    
    @handle_firebase_errors
    def verify_id_token(self, id_token: str, check_revoked: bool = True) -> dict:
        """Verify an ID token and return the decoded token."""
        return self.auth.verify_id_token(id_token, check_revoked=check_revoked)
    
    # Firestore Methods
    
    @handle_firebase_errors
    def get_document(self, collection: str, doc_id: str) -> Optional[dict]:
        """Get a document from Firestore."""
        doc_ref = self.db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        return doc.to_dict()
    
    @handle_firebase_errors
    def set_document(self, collection: str, doc_id: str, data: dict, merge: bool = False) -> None:
        """Set a document in Firestore."""
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.set(data, merge=merge)
    
    @handle_firebase_errors
    def update_document(self, collection: str, doc_id: str, updates: dict) -> None:
        """Update a document in Firestore."""
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.update(updates)
    
    @handle_firebase_errors
    def delete_document(self, collection: str, doc_id: str) -> None:
        """Delete a document from Firestore."""
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.delete()
    
    @handle_firebase_errors
    def query_collection(
        self,
        collection: str,
        field: str,
        op: str,
        value: Any,
        limit: Optional[int] = None
    ) -> List[dict]:
        """Query a collection in Firestore."""
        query = self.db.collection(collection).where(field, op, value)
        
        if limit is not None:
            query = query.limit(limit)
            
        return [doc.to_dict() for doc in query.stream()]
    
    # Storage Methods
    
    @handle_firebase_errors
    def upload_file(
        self,
        file_path: str,
        destination_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to Firebase Storage.
        
        Args:
            file_path: Path to the local file to upload.
            destination_path: Path where the file will be stored in the bucket.
            content_type: MIME type of the file.
            metadata: Additional metadata for the file.
            
        Returns:
            The public URL of the uploaded file.
        """
        blob = self.storage_bucket.blob(destination_path)
        
        if content_type:
            blob.content_type = content_type
            
        if metadata:
            blob.metadata = metadata
            
        blob.upload_from_filename(file_path)
        blob.make_public()
        
        return blob.public_url
    
    @handle_firebase_errors
    def download_file(self, source_path: str, destination_path: str) -> None:
        """
        Download a file from Firebase Storage.
        
        Args:
            source_path: Path to the file in the bucket.
            destination_path: Local path where the file will be saved.
        """
        blob = self.storage_bucket.blob(source_path)
        blob.download_to_filename(destination_path)
    
    @handle_firebase_errors
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from Firebase Storage.
        
        Args:
            file_path: Path to the file in the bucket.
        """
        blob = self.storage_bucket.blob(file_path)
        blob.delete()
    
    @handle_firebase_errors
    def get_file_url(self, file_path: str) -> str:
        """
        Get the public URL of a file in Firebase Storage.
        
        Args:
            file_path: Path to the file in the bucket.
            
        Returns:
            The public URL of the file.
        """
        blob = self.storage_bucket.blob(file_path)
        return blob.public_url

# Create a singleton instance
firebase_service = FirebaseService()

def init_firebase(app) -> None:
    """Initialize the Firebase service with the Flask app."""
    firebase_service.init_app(app)
