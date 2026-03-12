output "vm_public_ip" {
  description = "Adresse IP publique de la VM"
  value       = azurerm_public_ip.public_ip.ip_address
}

output "vm_admin_username" {
  description = "Nom d'utilisateur admin"
  value       = var.admin_username
}

output "ssh_private_key" {
  description = "Clé privée SSH (à sauvegarder pour se connecter)"
  value       = tls_private_key.ssh_key.private_key_pem
  sensitive   = true
}

output "storage_account_name" {
  description = "Nom du Storage Account"
  value       = azurerm_storage_account.storage.name
}

output "storage_primary_access_key" {
  description = "Clé d'accès primaire du Storage Account"
  value       = azurerm_storage_account.storage.primary_access_key
  sensitive   = true
}

output "storage_blob_endpoint" {
  description = "URL du Blob Storage"
  value       = azurerm_storage_account.storage.primary_blob_endpoint
}

output "storage_container_name" {
  description = "Nom du conteneur Blob"
  value       = azurerm_storage_container.container.name
}

output "app_url" {
  description = "URL de l'application Flask"
  value       = "http://${azurerm_public_ip.public_ip.ip_address}:5000"
}
