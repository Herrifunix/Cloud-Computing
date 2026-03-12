# Rapport - TP Cloud Computing

## Deploiement automatise d'une application Flask sur Azure avec Terraform

---

## Table des matieres

1. [Introduction](#1-introduction)
2. [Architecture du projet](#2-architecture-du-projet)
3. [Etape 1 : Configuration de l'environnement](#3-etape-1--configuration-de-lenvironnement)
4. [Etape 2 : Code Terraform (Infrastructure as Code)](#4-etape-2--code-terraform-infrastructure-as-code)
5. [Etape 3 : Backend Flask (API CRUD)](#5-etape-3--backend-flask-api-crud)
6. [Etape 4 : Deploiement de l'infrastructure](#6-etape-4--deploiement-de-linfrastructure)
7. [Etape 5 : Tests et validation](#7-etape-5--tests-et-validation)
8. [Etape 6 : Suppression de l'infrastructure](#8-etape-6--suppression-de-linfrastructure)
9. [Problemes rencontres et solutions](#9-problemes-rencontres-et-solutions)
10. [Conclusion](#10-conclusion)

---

## 1. Introduction

L'objectif de ce TP est de deployer automatiquement une application web sur Azure en utilisant Terraform comme outil d'Infrastructure as Code (IaC). Le projet comprend :

- Une VM Ubuntu hebergeant un backend Flask avec Gunicorn
- Un Azure Blob Storage pour le stockage de fichiers
- L'infrastructure reseau necessaire (VNet, Subnet, NSG, IP publique)
- Un script de provisioning automatique

L'application expose une API REST permettant d'effectuer des operations CRUD (Create, Read, Update, Delete) sur des fichiers stockes dans Azure Blob Storage.

---

## 2. Architecture du projet

```
Client (curl / Postman / Navigateur)
        |
        | HTTP port 5000
        v
+-------------------+          +---------------------------+
|   VM Ubuntu 22.04 |          |   Azure Blob Storage      |
|   (Flask+Gunicorn) | <------> |   Container: staticfiles  |
|   Standard_D2s_v3 |   SDK    |   _metadata.json          |
+-------------------+          +---------------------------+
        |
        | SSH (port 22)
        |
+-------------------+
|   Reseau Azure    |
|   VNet 10.0.0.0/16|
|   Subnet /24      |
|   NSG (22, 5000)  |
|   IP publique     |
+-------------------+
```

### Ressources Azure deployees

| Ressource | Nom | Description |
|-----------|-----|-------------|
| Resource Group | rg-tp-cloud | Groupe de ressources principal |
| Virtual Network | vnet-tp-cloud | Reseau virtuel (10.0.0.0/16) |
| Subnet | subnet-tp-cloud | Sous-reseau (10.0.1.0/24) |
| Public IP | pip-tp-cloud | IP publique statique de la VM |
| NSG | nsg-tp-cloud | Regles de securite (SSH + HTTP 5000) |
| NIC | nic-tp-cloud | Interface reseau de la VM |
| VM | vm-tp-cloud | Machine virtuelle Ubuntu 22.04 LTS |
| Storage Account | stcloudpierre2026 | Compte de stockage blob |
| Container | staticfiles | Conteneur pour les fichiers uploades |

---

## 3. Etape 1 : Configuration de l'environnement

### Outils installes

- **Terraform** v1.14.7 : Outil d'IaC pour provisionner l'infrastructure Azure
- **Azure CLI** v2.84.0 : Interface en ligne de commande pour interagir avec Azure
- **PowerShell** : Terminal utilise sur Windows

### Connexion Azure

```powershell
az login
az account show --query "{name:name,id:id}" -o table
```

La subscription utilisee est **Azure for Students**.

> *[Capture d'ecran : resultat de `az account show`]*

### Initialisation Terraform

```powershell
terraform init
```

Cette commande telecharge les providers necessaires :
- `hashicorp/azurerm` v3.117.1 (gestion des ressources Azure)
- `hashicorp/tls` v4.2.1 (generation de la cle SSH)

> *[Capture d'ecran : sortie de `terraform init`]*

---

## 4. Etape 2 : Code Terraform (Infrastructure as Code)

Le code Terraform est reparti en 4 fichiers :

### provider.tf

Configure le provider Azure (azurerm ~> 3.0) et passe le `subscription_id` en variable pour eviter de le coder en dur.

### variables.tf

Declare 7 variables parametrables :
- `subscription_id` : identifiant de la subscription Azure
- `resource_group_name` : nom du resource group (defaut : `rg-tp-cloud`)
- `location` : region Azure (defaut : `France Central`)
- `vm_size` : taille de la VM (defaut : `Standard_D2s_v3`)
- `admin_username` : utilisateur SSH (defaut : `azureuser`)
- `storage_account_name` : nom globalement unique du storage (defaut : `stcloudpierre2026`)
- `container_name` : nom du conteneur blob (defaut : `staticfiles`)

Les valeurs sont fournies via `terraform.tfvars` (non versionne, un `.example` est fourni).

### main.tf

Contient toutes les ressources Azure :

1. **Resource Group** : conteneur logique pour toutes les ressources
2. **VNet + Subnet** : reseau virtuel prive avec un sous-reseau /24
3. **IP publique** : allocation statique, SKU Standard
4. **NSG** : deux regles entrantes :
   - Port 22 (SSH) pour l'administration
   - Port 5000 (HTTP) pour l'application Flask
5. **NIC** : interface reseau associee au subnet et a l'IP publique
6. **Cle SSH** : generee automatiquement par Terraform (RSA 4096 bits) via le provider `tls`, ce qui evite de gerer manuellement les cles
7. **VM Linux** : Ubuntu 22.04 LTS, provisionne automatiquement via :
   - `provisioner "file"` : copie le dossier `app/` et le script `setup.sh` sur la VM
   - `provisioner "remote-exec"` : execute `setup.sh` avec les credentials du storage
8. **Storage Account** : compte de stockage blob avec replication LRS et regles CORS
9. **Container** : conteneur blob prive pour les fichiers

### outputs.tf

Expose 8 sorties apres le deploiement :
- IP publique de la VM
- Nom d'utilisateur admin
- Cle privee SSH (sensible)
- Nom et cle d'acces du storage (sensible)
- Endpoint blob et nom du conteneur
- URL de l'application (`http://<IP>:5000`)

---

## 5. Etape 3 : Backend Flask (API CRUD)

### app/app.py

L'application Flask expose les endpoints suivants :

| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Page d'accueil avec liste des endpoints |
| GET | `/health` | Healthcheck (verifie la connexion au storage) |
| POST | `/files` | Upload d'un fichier (multipart/form-data) |
| GET | `/files` | Liste tous les fichiers uploades |
| GET | `/files/<id>` | Telecharge un fichier par son ID |
| DELETE | `/files/<id>` | Supprime un fichier par son ID |

### Fonctionnement

- Chaque fichier uploade recoit un UUID unique
- Le fichier est stocke dans Azure Blob Storage sous le nom `{uuid}_{original_name}`
- Les metadonnees (id, nom original, type MIME, date) sont stockees dans un blob `_metadata.json`
- Le telechargement et la suppression se font via l'ID du fichier

### Dependances (requirements.txt)

- `flask>=3.0` : framework web
- `azure-storage-blob>=12.0` : SDK Azure pour le Blob Storage
- `python-dotenv>=1.0` : chargement des variables d'environnement
- `gunicorn>=21.0` : serveur WSGI pour la production

### setup.sh (script de provisioning)

Le script effectue les operations suivantes sur la VM :
1. Attend la liberation des verrous apt (probleme frequent sur les VMs fraichement creees)
2. Installe Python 3, pip et venv
3. Cree un environnement virtuel Python
4. Installe les dependances depuis `requirements.txt`
5. Genere le fichier `.env` avec les credentials du storage (passes en arguments par Terraform)
6. Cree un service systemd `flask-app` pour lancer Gunicorn au demarrage
7. Active et demarre le service

---

## 6. Etape 4 : Deploiement de l'infrastructure

### Commandes executees

```powershell
terraform plan    # Verification du plan d'execution
terraform apply   # Deploiement effectif (confirmation requise)
```

`terraform plan` affiche les 10 ressources a creer et permet de verifier avant d'appliquer.

> *[Capture d'ecran : sortie de `terraform plan` montrant les ressources planifiees]*

`terraform apply` cree les ressources dans l'ordre des dependances :
1. Resource Group
2. VNet, Subnet, IP publique, NSG (en parallele)
3. NIC et association NIC-NSG
4. Storage Account et Container
5. Cle SSH
6. VM (avec provisioning automatique)

> *[Capture d'ecran : sortie de `terraform apply` - creation reussie]*

### Resultat

Apres le deploiement, Terraform affiche les sorties :

```
app_url = "http://<IP_PUBLIQUE>:5000"
vm_public_ip = "<IP_PUBLIQUE>"
```

> *[Capture d'ecran : sorties Terraform apres `apply`]*

---

## 7. Etape 5 : Tests et validation

### Test 1 : Acces a l'application via l'IP publique

```powershell
curl.exe http://<VM_IP>:5000/
```

Resultat : l'API repond avec la liste des endpoints disponibles.

> *[Capture d'ecran : reponse de GET /]*

### Test 2 : Healthcheck (connexion au storage)

```powershell
curl.exe http://<VM_IP>:5000/health
```

Resultat attendu :
```json
{"status": "healthy", "storage": "connected"}
```

Ce test verifie que la VM communique correctement avec Azure Blob Storage.

> *[Capture d'ecran : reponse du healthcheck]*

### Test 3 : Upload d'un fichier (CREATE)

```powershell
echo "Hello Cloud Computing!" > test.txt
curl.exe -X POST -F "file=@test.txt" http://<VM_IP>:5000/files
```

Resultat attendu :
```json
{
  "message": "Fichier uploadé avec succès",
  "file": {
    "id": "<UUID>",
    "original_name": "test.txt",
    "blob_name": "<UUID>_test.txt",
    "content_type": "text/plain",
    "uploaded_at": "2026-03-12T..."
  }
}
```

> *[Capture d'ecran : reponse de POST /files]*

### Test 4 : Liste des fichiers (READ)

```powershell
curl.exe http://<VM_IP>:5000/files
```

Resultat : retourne la liste de tous les fichiers uploades avec leurs metadonnees.

> *[Capture d'ecran : reponse de GET /files]*

### Test 5 : Telechargement d'un fichier (READ)

```powershell
curl.exe http://<VM_IP>:5000/files/<file_id>
```

Resultat : retourne le contenu du fichier ("Hello Cloud Computing!").

> *[Capture d'ecran : reponse de GET /files/<id>]*

### Test 6 : Suppression d'un fichier (DELETE)

```powershell
curl.exe -X DELETE http://<VM_IP>:5000/files/<file_id>
```

Resultat attendu :
```json
{"message": "Fichier supprimé avec succès"}
```

Verification : un GET /files apres suppression confirme que le fichier n'est plus dans la liste.

> *[Capture d'ecran : reponse de DELETE /files/<id>]*

### Test 7 : Verification dans Azure Blob Storage

On peut verifier directement dans le portail Azure que les fichiers sont bien stockes dans le conteneur `staticfiles` du storage account `stcloudpierre2026`.

> *[Capture d'ecran : portail Azure montrant le conteneur blob avec les fichiers]*

---

## 8. Etape 6 : Suppression de l'infrastructure

Pour detruire toutes les ressources creees :

```powershell
terraform destroy
```

Cette commande supprime dans l'ordre inverse toutes les ressources :
- VM et son disque
- NIC, NSG, IP publique
- Subnet, VNet
- Storage Account et Container
- Resource Group

> *[Capture d'ecran : sortie de `terraform destroy`]*

---

## 9. Problemes rencontres et solutions

### Probleme 1 : Taille de VM non disponible

**Symptome** : Erreur `SkuNotAvailable` lors du `terraform apply` avec `Standard_B1s` et `Standard_B2s` dans la region France Central.

**Cause** : Certaines tailles de VM ne sont pas disponibles dans toutes les regions Azure, surtout avec les subscriptions etudiantes qui ont des quotas limites.

**Solution** : Changement de la taille de VM vers `Standard_D2s_v3` qui est disponible en France Central :
```hcl
vm_size = "Standard_D2s_v3"
```

### Probleme 2 : Region non autorisee

**Symptome** : Erreur `403 Forbidden` lors d'une tentative de deploiement sur `West Europe`.

**Cause** : La subscription Azure for Students applique des politiques (Azure Policy) qui restreignent les regions autorisees.

**Solution** : Utilisation de la region `France Central` (`francecentral`) qui est autorisee pour les subscriptions etudiantes.

### Probleme 3 : Nom de Storage Account deja pris

**Symptome** : Erreur `StorageAccountAlreadyTaken` car le nom `stcloudprojectpierre` etait deja utilise globalement.

**Cause** : Les noms de Storage Account Azure doivent etre **globalement uniques** a travers tous les clients Azure.

**Solution** : Changement vers un nom unique : `stcloudpierre2026`.

### Probleme 4 : Verrou apt lors du provisioning

**Symptome** : Le script `setup.sh` echoue (exit code 100) car `apt-get` est verrouille par un autre processus.

**Cause** : Sur les VMs fraichement creees, Ubuntu lance automatiquement des mises a jour en arriere-plan (`unattended-upgrades`), ce qui verrouille `apt`.

**Solution** : Ajout d'une boucle d'attente dans `setup.sh` qui patiente jusqu'a 10 minutes pour la liberation du verrou :
```bash
for i in $(seq 1 60); do
  if ! fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
    break
  fi
  sleep 10
done
```

### Probleme 5 : Provisioner file sous Windows

**Symptome** : Le `provisioner "file"` de Terraform copie `app/` comme un fichier unique au lieu d'un repertoire sur la VM.

**Cause** : Bug connu du provisioner file de Terraform sous Windows qui ne gere pas correctement la copie de repertoires.

**Solution** : Copie manuelle des fichiers via SCP, puis execution du script de provisioning via SSH :
```powershell
scp -i ssh_key -r app/* azureuser@<IP>:/home/azureuser/app/
ssh -i ssh_key azureuser@<IP> "sudo bash /home/azureuser/setup.sh ..."
```

### Probleme 6 : Desynchronisation du state Terraform

**Symptome** : Apres des echecs partiels de `terraform apply`, certaines ressources existent dans Azure mais pas dans le state Terraform, provoquant des conflits.

**Cause** : Lorsqu'un `apply` echoue a mi-parcours, les ressources deja creees ne sont pas enregistrees dans le state.

**Solution** : Utilisation de `terraform import` pour reimporter les ressources existantes dans le state :
```powershell
terraform import azurerm_virtual_network.vnet /subscriptions/.../virtualNetworks/vnet-tp-cloud
terraform import azurerm_storage_account.storage /subscriptions/.../storageAccounts/stcloudpierre2026
```

---

## 10. Conclusion

Ce projet a permis de mettre en pratique les concepts fondamentaux du Cloud Computing :

- **Infrastructure as Code** : Terraform permet de definir, versionner et reproduire l'infrastructure de maniere declarative. Toutes les ressources Azure sont decrites dans des fichiers `.tf`.

- **Provisioning automatise** : Le script `setup.sh` installe et configure automatiquement l'application sur la VM, rendant le deploiement reproductible.

- **Stockage cloud** : Azure Blob Storage offre un stockage scalable et resilient pour les fichiers, accessible via le SDK Python.

- **API REST** : Le backend Flask expose une API CRUD complete pour la gestion de fichiers, demontrant l'interaction entre une application et les services cloud.

- **Securite** : Les fichiers sensibles (`terraform.tfvars`, `.env`, `.tfstate`) sont exclus du depot Git via `.gitignore`. Les cles SSH sont generees automatiquement par Terraform et marquees comme sensibles.

### Stack technique

| Composant | Technologie |
|-----------|-------------|
| IaC | Terraform (azurerm ~> 3.0) |
| Cloud | Microsoft Azure |
| Compute | VM Ubuntu 22.04 LTS |
| Backend | Flask + Gunicorn |
| Stockage | Azure Blob Storage |
| SDK | azure-storage-blob (Python) |
| Provisioning | Bash (setup.sh) |
| Versioning | Git + GitHub |
