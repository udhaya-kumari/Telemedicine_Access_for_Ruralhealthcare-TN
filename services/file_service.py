import os
from uuid import uuid4

from werkzeug.utils import secure_filename


def ensure_upload_folder(upload_folder):
    os.makedirs(upload_folder, exist_ok=True)


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_uploaded_file(file_storage, upload_folder, allowed_extensions):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename, allowed_extensions):
        return None

    ensure_upload_folder(upload_folder)
    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid4().hex}.{extension}"
    path = os.path.join(upload_folder, stored_name)
    file_storage.save(path)
    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "file_path": path,
        "file_url": f"/uploads/{stored_name}",
        "file_type": extension,
    }
