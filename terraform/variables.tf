variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region to deploy resources"
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "GCP zone to deploy VM"
  type        = string
  default     = "us-central1-a"
}

variable "project_name" {
  description = "Project name — used as prefix for all resource names"
  type        = string
  default     = "microservices-sre"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod"
  }
}

variable "machine_type" {
  description = "GCP VM machine type"
  type        = string
  default     = "e2-micro"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 20
}

variable "ssh_cidr_block" {
  description = "CIDR block allowed to SSH into the instance (use your IP: x.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "public_key_material" {
  description = "SSH public key material (contents of ~/.ssh/id_rsa.pub)"
  type        = string
}

variable "app_repo_url" {
  description = "Git repo URL to clone on the server"
  type        = string
  default     = ""
}