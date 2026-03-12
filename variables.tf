variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "resource_group_name" {
  description = "Nom du Resource Group"
  type        = string
  default     = "rg-tp-cloud-pierre-zhou-2026"
}

variable "location" {
  description = "Région Azure"
  type        = string
  default     = "France Central"
}

variable "vm_size" {
  description = "Taille de la VM"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "admin_username" {
  description = "Nom d'utilisateur admin de la VM"
  type        = string
  default     = "azureuser"
}

variable "storage_account_name" {
  description = "Nom du Storage Account (doit être unique et en minuscules, 3-24 chars)"
  type        = string
  default     = "stcloudpierre2026"
}

variable "container_name" {
  description = "Nom du conteneur Blob Storage"
  type        = string
  default     = "staticfiles"
}

