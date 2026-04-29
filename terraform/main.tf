terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# ────────────────────────────────────────────
# Firewall (equivalent of Security Group)
# ────────────────────────────────────────────
resource "google_compute_firewall" "microservices_sg" {
  name    = "${var.project_name}-sg"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  allow {
    protocol = "tcp"
    ports    = ["3002"]
  }

  allow {
    protocol = "tcp"
    ports    = ["3000"]
  }

  allow {
    protocol = "tcp"
    ports    = ["9090"]
  }

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]

  target_tags = ["microservices"]

  description = "Firewall for microservices deployment"
}

# ────────────────────────────────────────────
# SSH Key (equivalent of Key Pair)
# ────────────────────────────────────────────
# GCP does not use separate key resources → handled in metadata

# ────────────────────────────────────────────
# VM Instance (equivalent of EC2)
# ────────────────────────────────────────────
resource "google_compute_instance" "microservices_server" {
  name         = "${var.project_name}-server"
  machine_type = var.machine_type
  zone         = var.gcp_zone
  allow_stopping_for_update = true

  tags = ["microservices"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.disk_size_gb
    }
  }

  network_interface {
    network = "default"

    access_config {}  # Public IP (equivalent of Elastic IP)
  }

  metadata = {
    ssh-keys = "ubuntu:${var.public_key_material}"
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e

    echo "=== Updating system ==="
    apt-get update -y
    apt-get upgrade -y

    echo "=== Installing dependencies ==="
    apt-get install -y ca-certificates curl gnupg lsb-release git

    echo "=== Installing Docker ==="
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
      gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu

    echo "=== Deploying application ==="
    cd /home/ubuntu

    if [ -n "${var.app_repo_url}" ]; then
      git clone ${var.app_repo_url} app
      cd app
      docker compose up -d --build
    else
      echo "No repository URL provided. Skipping deployment."
    fi

    echo "=== Setup complete ==="
  EOF
}