terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
  subscription_id = "f4322e67-879b-4627-ac58-9eeae93247d5"  
  resource_provider_registrations = "none"

}

variable "location" { default = "francecentral" }
variable "suffix"   { default = "iiboudi07" }   # lowercase letters/digits only, must be globally unique

data "azurerm_client_config" "me" {}

resource "azurerm_resource_group" "rg" {
  name     = "rg-telecom-${var.suffix}"
  location = var.location
}

resource "azurerm_storage_account" "lake" {
  name                      = "sttelecom${var.suffix}"
  resource_group_name       = azurerm_resource_group.rg.name
  location                  = var.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  is_hns_enabled            = true
  shared_access_key_enabled = false
}

resource "azurerm_role_assignment" "me" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.me.object_id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(["bronze", "silver", "gold", "quarantine"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id
  depends_on         = [azurerm_role_assignment.me]
}

output "storage_account" { value = azurerm_storage_account.lake.name }