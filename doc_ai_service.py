"""Document AI service wrapper for use by the web app and CLI."""

import os
import tempfile
from dotenv import load_dotenv
from sap_business_document_processing import DoxApiClient
from sap_business_document_processing.document_information_extraction_client.constants import (
    CONTENT_TYPE_PDF,
    CONTENT_TYPE_PNG,
    CONTENT_TYPE_JPEG,
    CONTENT_TYPE_TIFF,
    CONTENT_TYPE_UNKNOWN,
)

# Image rotation support
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

load_dotenv()


def rotate_image(file_path, rotation=0):
    """
    Rotate an image file by the specified degrees (90, 180, 270).
    Also applies EXIF rotation if present.
    Returns the path to the rotated image (may be same file if no rotation needed).
    """
    if not HAS_PIL:
        return file_path
    
    try:
        ext = file_path.lower().split(".")[-1]
        if ext not in ("jpg", "jpeg", "png", "tiff", "tif"):
            return file_path  # Only rotate image files
        
        with Image.open(file_path) as img:
            # Apply EXIF orientation first
            try:
                from PIL import ExifTags
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = img._getexif()
                if exif:
                    orientation_val = exif.get(orientation, 1)
                    if orientation_val == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation_val == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation_val == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, TypeError):
                pass
            
            # Apply manual rotation
            if rotation in (90, 180, 270):
                img = img.rotate(-rotation, expand=True)  # PIL rotates counter-clockwise
            
            # Save rotated image
            rotated_path = file_path.replace(".", "_rotated.")
            img.save(rotated_path)
            return rotated_path
    except Exception as e:
        print(f"[WARN] Image rotation failed: {e}")
        return file_path

# Default extraction field sets (invoice)
HEADER_FIELDS = [
    "documentNumber",
    "taxId",
    "purchaseOrderNumber",
    "shippingAmount",
    "netAmount",
    "senderAddress",
    "senderName",
    "grossAmount",
    "currencyCode",
    "receiverContact",
    "documentDate",
    "taxAmount",
    "taxRate",
    "receiverName",
    "receiverAddress",
]
LINE_ITEM_FIELDS = [
    "description",
    "netAmount",
    "quantity",
    "unitPrice",
]

MIME_MAP = {
    "application/pdf": CONTENT_TYPE_PDF,
    "image/png": CONTENT_TYPE_PNG,
    "image/jpeg": CONTENT_TYPE_JPEG,
    "image/jpg": CONTENT_TYPE_JPEG,
    "image/tiff": CONTENT_TYPE_TIFF,
}


def _get_client():
    # Support both DOX_* prefix (Render) and plain names (.env local)
    url = os.getenv("DOX_URL") or os.getenv("URL")
    client_id = os.getenv("DOX_CLIENT_ID") or os.getenv("CLIENT_ID")
    client_secret = os.getenv("DOX_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
    uaa_url = os.getenv("DOX_UAADOMAIN") or os.getenv("UAADOMAIN")
    if not all([url, client_id, client_secret, uaa_url]):
        raise ValueError(
            "Missing Document AI credentials. Set DOX_URL, DOX_CLIENT_ID, DOX_CLIENT_SECRET, DOX_UAADOMAIN"
        )
    return DoxApiClient(url, client_id, client_secret, uaa_url)


def get_capabilities():
    """Return Document AI capabilities (document types and fields)."""
    return _get_client().get_capabilities()


def extract_from_file(file_stream, filename, document_type="invoice", client_id="default", rotation=0):
    """
    Extract header and line items from an uploaded document.
    file_stream: file-like object (e.g. request.files["file"].stream).
    filename: original filename (used for content type detection).
    rotation: degrees to rotate image (0, 90, 180, 270).
    """
    client = _get_client()
    content_type = MIME_MAP.get(
        _guess_mime(filename), CONTENT_TYPE_UNKNOWN
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=_suffix(filename)) as tmp:
        tmp.write(file_stream.read())
        tmp_path = tmp.name
    
    # Apply rotation if needed
    rotated_path = None
    if rotation or _is_image(filename):
        rotated_path = rotate_image(tmp_path, rotation)
        if rotated_path != tmp_path:
            print(f"[INFO] Rotated image {rotation}° -> {rotated_path}")
            tmp_path = rotated_path
    
    try:
        # Try extraction with default fields first
        result = client.extract_information_from_document(
            document_path=tmp_path,
            client_id=client_id,
            document_type=document_type,
            mime_type=content_type,
            header_fields=HEADER_FIELDS,
            line_item_fields=LINE_ITEM_FIELDS,
        )
        # Log result summary
        print(f"[INFO] Extraction complete for {filename}: status={result.get('status', 'unknown')}")
        
        return result
    except Exception as e:
        print(f"[ERROR] Extraction failed for {filename}: {e}")
        raise
    finally:
        # Clean up temp files
        paths_to_clean = set(filter(None, [tmp_path, rotated_path]))
        for path in paths_to_clean:
            try:
                os.unlink(path)
            except OSError:
                pass


def _is_image(filename):
    ext = (filename or "").lower().split(".")[-1]
    return ext in ("jpg", "jpeg", "png", "tiff", "tif")


def _guess_mime(filename):
    ext = (filename or "").lower().split(".")[-1]
    mime = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    return mime.get(ext, "application/octet-stream")


def _suffix(filename):
    ext = (filename or "").lower().split(".")[-1]
    if ext in ("pdf", "png", "jpg", "jpeg", "tiff", "tif"):
        return "." + ext
    return ".pdf"
