import os
import mimetypes
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from google.cloud.exceptions import NotFound
from firebase_admin import storage as firebase_storage
from .utils import allowed_file

class StorageManager:
    """
    A utility class to handle file uploads to Firebase Storage.
    """
    
    def __init__(self, app=None):
        self.app = app
        self.bucket = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the storage with the Flask app."""
        self.app = app
        self.bucket_name = app.config.get('FIREBASE_STORAGE_BUCKET')
        if not self.bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET not configured")
        self.bucket = firebase_storage.bucket(self.bucket_name)
    
    def upload_file(self, file, destination_path, public=False, content_type=None):
        """
        Upload a file to Firebase Storage.
        
        Args:
            file: File object or file path to upload
            destination_path: Path in the storage bucket where the file will be stored
            public: If True, makes the file publicly accessible
            content_type: MIME type of the file (auto-detected if not provided)
            
        Returns:
            dict: File metadata including download URL and path
        """
        if not self.bucket:
            raise RuntimeError("Storage not initialized. Call init_app first.")
        
        # If file is a string, treat it as a file path
        if isinstance(file, str):
            if not os.path.isfile(file):
                raise FileNotFoundError(f"File not found: {file}")
            
            filename = os.path.basename(file)
            blob = self.bucket.blob(os.path.join(destination_path, filename))
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(file)
                
            blob.upload_from_filename(
                file,
                content_type=content_type
            )
        else:
            # Handle file-like object (e.g., from request.files)
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("Invalid filename")
                
            if not allowed_file(filename):
                raise ValueError(f"File type not allowed: {filename}")
            
            blob = self.bucket.blob(os.path.join(destination_path, filename))
            
            # Detect content type if not provided
            if not content_type:
                content_type = file.content_type or mimetypes.guess_type(filename)[0]
            
            # For in-memory files (like from request.files)
            file.seek(0)  # Ensure we're at the start of the file
            blob.upload_from_string(
                file.read(),
                content_type=content_type
            )
        
        # Make the file publicly accessible if requested
        if public:
            blob.make_public()
        
        # Generate a signed URL that's valid for 7 days
        expiration = datetime.utcnow() + timedelta(days=7)
        download_url = blob.generate_signed_url(expiration=expiration)
        
        return {
            'name': blob.name,
            'content_type': blob.content_type,
            'size': blob.size,
            'public_url': blob.public_url if public else None,
            'signed_url': download_url,
            'bucket': self.bucket_name,
            'path': f"gs://{self.bucket_name}/{blob.name}",
            'updated': blob.updated,
            'metadata': blob.metadata or {}
        }
    
    def delete_file(self, file_path):
        """
        Delete a file from Firebase Storage.
        
        Args:
            file_path: Path to the file in the storage bucket
            
        Returns:
            bool: True if the file was deleted, False if it didn't exist
        """
        if not self.bucket:
            raise RuntimeError("Storage not initialized. Call init_app first.")
            
        blob = self.bucket.blob(file_path)
        
        try:
            blob.delete()
            return True
        except NotFound:
            return False
    
    def get_file_url(self, file_path, signed=True, expiration_hours=168):
        """
        Get a download URL for a file.
        
        Args:
            file_path: Path to the file in the storage bucket
            signed: If True, returns a signed URL (default: True)
            expiration_hours: Number of hours until the signed URL expires (default: 7 days)
            
        Returns:
            str: The download URL, or None if the file doesn't exist
        """
        if not self.bucket:
            raise RuntimeError("Storage not initialized. Call init_app first.")
            
        blob = self.bucket.blob(file_path)
        
        if not blob.exists():
            return None
            
        if signed:
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
            return blob.generate_signed_url(expiration=expiration)
        else:
            blob.make_public()
            return blob.public_url
    
    def list_files(self, prefix='', delimiter='/'):
        """
        List files in the storage bucket.
        
        Args:
            prefix: Filter files with this prefix
            delimiter: Used to simulate directory-like behavior
            
        Returns:
            tuple: (files, prefixes) where files is a list of file blobs and 
                   prefixes is a list of folder-like prefixes
        """
        if not self.bucket:
            raise RuntimeError("Storage not initialized. Call init_app first.")
            
        blobs = self.bucket.list_blobs(prefix=prefix, delimiter=delimiter)
        
        # Get the list of files and prefixes (folders)
        files = list(blobs)
        prefixes = list(blobs.prefixes)
        
        return files, prefixes

# Create a default instance for easy importing
storage = StorageManager()
