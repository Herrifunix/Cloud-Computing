import os
import json
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file
from azure.storage.blob import BlobServiceClient
from io import BytesIO

app = Flask(__name__)

# ─── Configuration Azure Blob Storage ───
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "")
AZURE_STORAGE_KEY = os.environ.get("AZURE_STORAGE_KEY", "")
AZURE_CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME", "staticfiles")

METADATA_BLOB = "_metadata.json"


def get_blob_service():
    """Crée un client BlobServiceClient."""
    connection_string = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={AZURE_STORAGE_ACCOUNT};"
        f"AccountKey={AZURE_STORAGE_KEY};"
        f"EndpointSuffix=core.windows.net"
    )
    return BlobServiceClient.from_connection_string(connection_string)


def get_container_client():
    """Retourne le client du conteneur blob."""
    return get_blob_service().get_container_client(AZURE_CONTAINER_NAME)


# ─── Helpers métadonnées ───
def load_metadata():
    """Charge les métadonnées depuis le blob _metadata.json."""
    container = get_container_client()
    try:
        blob = container.get_blob_client(METADATA_BLOB)
        data = blob.download_blob().readall()
        return json.loads(data)
    except Exception:
        return {}


def save_metadata(metadata):
    """Sauvegarde les métadonnées dans le blob _metadata.json."""
    container = get_container_client()
    blob = container.get_blob_client(METADATA_BLOB)
    blob.upload_blob(json.dumps(metadata, indent=2), overwrite=True)


# ═══════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════

@app.route("/")
def index():
    return jsonify({
        "message": "API Flask - Cloud Computing Project",
        "endpoints": {
            "GET /files": "Lister tous les fichiers",
            "POST /files": "Uploader un fichier (multipart/form-data, champ 'file')",
            "GET /files/<file_id>": "Télécharger un fichier",
            "DELETE /files/<file_id>": "Supprimer un fichier",
            "GET /health": "Vérifier la santé de l'application",
        }
    })


@app.route("/health")
def health():
    """Endpoint de santé pour vérifier la connexion au storage."""
    try:
        container = get_container_client()
        container.get_container_properties()
        return jsonify({"status": "healthy", "storage": "connected"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


# ─── CREATE : Upload d'un fichier ───
@app.route("/files", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni (champ 'file' requis)"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nom de fichier vide"}), 400

    file_id = str(uuid.uuid4())
    blob_name = f"{file_id}_{file.filename}"

    # Upload vers Azure Blob Storage
    container = get_container_client()
    blob_client = container.get_blob_client(blob_name)
    blob_client.upload_blob(file.read(), overwrite=True)

    # Sauvegarder les métadonnées
    metadata = load_metadata()
    metadata[file_id] = {
        "id": file_id,
        "original_name": file.filename,
        "blob_name": blob_name,
        "content_type": file.content_type,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    save_metadata(metadata)

    return jsonify({
        "message": "Fichier uploadé avec succès",
        "file": metadata[file_id]
    }), 201


# ─── READ : Lister tous les fichiers ───
@app.route("/files", methods=["GET"])
def list_files():
    metadata = load_metadata()
    return jsonify({"files": list(metadata.values()), "count": len(metadata)})


# ─── READ : Télécharger un fichier ───
@app.route("/files/<file_id>", methods=["GET"])
def download_file(file_id):
    metadata = load_metadata()
    if file_id not in metadata:
        return jsonify({"error": "Fichier non trouvé"}), 404

    file_info = metadata[file_id]
    container = get_container_client()
    blob_client = container.get_blob_client(file_info["blob_name"])

    try:
        stream = blob_client.download_blob()
        data = BytesIO(stream.readall())
        return send_file(
            data,
            download_name=file_info["original_name"],
            mimetype=file_info.get("content_type", "application/octet-stream"),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── DELETE : Supprimer un fichier ───
@app.route("/files/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    metadata = load_metadata()
    if file_id not in metadata:
        return jsonify({"error": "Fichier non trouvé"}), 404

    file_info = metadata[file_id]

    # Supprimer le blob
    container = get_container_client()
    blob_client = container.get_blob_client(file_info["blob_name"])
    try:
        blob_client.delete_blob()
    except Exception:
        pass

    # Supprimer la métadonnée
    del metadata[file_id]
    save_metadata(metadata)

    return jsonify({"message": "Fichier supprimé", "id": file_id})


# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
