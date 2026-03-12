# TP Cloud Computing - Deploiement Automatise avec Terraform

## Objectif
Deployer automatiquement sur Azure :
- une VM Ubuntu (backend Flask)
- un Blob Storage pour les fichiers statiques
- le reseau necessaire (VNet, subnet, NSG, IP publique)

Le backend expose une API CRUD de fichiers connectee a Azure Blob Storage.

## Architecture
```
Client (curl/Postman)
    |
    | HTTP :5000
    v
VM Ubuntu (Flask + Gunicorn) <----> Azure Blob Storage (container: staticfiles)
```

## Prerequis
- Terraform >= 1.0
- Azure CLI >= 2.0
- Un abonnement Azure actif
- PowerShell (Windows)

## Configuration des fichiers

### 1. Terraform variables
Copier le fichier exemple :

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
```

Puis completer `terraform.tfvars` :
- `subscription_id`
- `resource_group_name` (ex: `rg-tp-cloud`)
- `location` (ex: `francecentral`)
- `vm_size` (ex: `Standard_D2s_v3`)
- `admin_username` (ex: `azureuser`)
- `storage_account_name` (doit etre globalement unique)
- `container_name` (ex: `staticfiles`)

### 2. Variables d'environnement backend
Copier l'exemple :

```powershell
Copy-Item app/.env.example app/.env
```

Puis completer `app/.env` :
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_KEY`
- `AZURE_CONTAINER_NAME`

Note : en production sur la VM, ces valeurs sont injectees automatiquement par Terraform via `setup.sh`.

## Deploiement (Azure)

### 1. Connexion Azure
```powershell
az login
```

### 2. Verification de la subscription active
```powershell
az account show --query "{name:name,id:id}" -o table
```

### 3. Initialisation Terraform
```powershell
terraform init
```

### 4. Verification du plan
```powershell
terraform plan
```

### 5. Application
```powershell
terraform apply
```

### 6. Recuperer les sorties utiles
```powershell
terraform output app_url
terraform output vm_public_ip
```

## Tests API

### Healthcheck
```powershell
curl.exe http://<VM_IP>:5000/health
```

### Upload
```powershell
curl.exe -X POST -F "file=@test.txt" http://<VM_IP>:5000/files
```

### Liste
```powershell
curl.exe http://<VM_IP>:5000/files
```

### Download
```powershell
curl.exe http://<VM_IP>:5000/files/<file_id>
```

### Delete
```powershell
curl.exe -X DELETE http://<VM_IP>:5000/files/<file_id>
```

## Lancement local du backend (optionnel)

Depuis le dossier racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
python app/app.py
```

Application locale : `http://127.0.0.1:5000`

## Structure du projet
```
.
├── provider.tf
├── variables.tf
├── main.tf
├── outputs.tf
├── terraform.tfvars            # local
├── terraform.tfvars.example    # versionne
├── setup.sh
├── app/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env                    # local
│   └── .env.example            # versionne
├── .gitignore
└── README.md
```

## Push GitHub (recommande)

Fichiers a versionner :
- `*.tf`
- `terraform.tfvars.example`
- `app/.env.example`
- `setup.sh`
- code backend
- `README.md`

Fichiers a ne pas versionner (deja ignores) :
- `terraform.tfvars`
- `*.tfstate*`
- `.terraform/`
- `app/.env`

## Suppression de l'infrastructure
```powershell
terraform destroy
```

## Stack technique
- Terraform
- Azure (Compute, Network, Storage)
- Flask
- Gunicorn
- azure-storage-blob (SDK Python)
