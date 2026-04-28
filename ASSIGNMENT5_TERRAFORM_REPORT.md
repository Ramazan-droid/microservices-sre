# Assignment 5 — Terraform Infrastructure as Code Report

---

## 1. Overview

This report documents the Terraform-based infrastructure provisioning for the Microservices SRE project. Infrastructure as Code (IaC) enables reproducible, version-controlled, automated deployments.

---

## 2. Terraform File Structure

```
terraform/
├── main.tf                   # Core resource definitions
├── variables.tf              # Input variable declarations
├── outputs.tf                # Output value declarations
└── terraform.tfvars.example  # Example values (template)
```

---

## 3. Resources Provisioned

### main.tf — Resources

| Resource | Type | Purpose |
|----------|------|---------|
| `aws_security_group.microservices_sg` | Security Group | Network access rules |
| `aws_key_pair.microservices_key` | Key Pair | SSH access |
| `data.aws_ami.ubuntu` | Data Source | Latest Ubuntu 22.04 AMI |
| `aws_instance.microservices_server` | EC2 Instance | Application server |
| `aws_eip.microservices_eip` | Elastic IP | Static public IP |

### Network Access Rules (Security Group)

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 80 | TCP | 0.0.0.0/0 | HTTP — Frontend |
| 3000 | TCP | 0.0.0.0/0 | Grafana |
| 9090 | TCP | 0.0.0.0/0 | Prometheus |
| 22 | TCP | Configurable | SSH |
| All | All | 0.0.0.0/0 | Outbound |

---

## 4. variables.tf — Input Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `aws_region` | string | us-east-1 | Deployment region |
| `aws_access_key` | string | — (sensitive) | AWS access key |
| `aws_secret_key` | string | — (sensitive) | AWS secret key |
| `project_name` | string | microservices-sre | Resource name prefix |
| `environment` | string | dev | dev/staging/prod |
| `instance_type` | string | t3.medium | EC2 instance type |
| `volume_size_gb` | number | 30 | Root disk size |
| `ssh_cidr_block` | string | 0.0.0.0/0 | SSH source CIDR |
| `public_key_material` | string | — | SSH public key |
| `app_repo_url` | string | — | Git repo to clone |

---

## 5. outputs.tf — Outputs

| Output | Description |
|--------|-------------|
| `instance_id` | EC2 instance ID |
| `public_ip` | Elastic IP address |
| `public_dns` | Public DNS name |
| `frontend_url` | http://{ip} — application URL |
| `grafana_url` | http://{ip}:3000 |
| `prometheus_url` | http://{ip}:9090 |
| `ssh_command` | Ready-to-use SSH command |
| `security_group_id` | Security group ID |

---

## 6. Deployment Steps

### Prerequisites
```bash
# Install Terraform
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# Verify
terraform version
```

### Step 1: Initialize

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your AWS credentials and SSH key

terraform init
```

Output:
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.x.x...
Terraform has been successfully initialized!
```

### Step 2: Plan

```bash
terraform plan
```

Output summary:
```
Plan: 5 to add, 0 to change, 0 to destroy.

  + aws_security_group.microservices_sg
  + aws_key_pair.microservices_key
  + aws_instance.microservices_server
  + aws_eip.microservices_eip
  (data) aws_ami.ubuntu (will be read)
```

### Step 3: Apply

```bash
terraform apply
# Type 'yes' when prompted

# After ~3 minutes:
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
  frontend_url    = "http://54.x.x.x"
  grafana_url     = "http://54.x.x.x:3000"
  prometheus_url  = "http://54.x.x.x:9090"
  ssh_command     = "ssh -i ~/.ssh/id_rsa ubuntu@54.x.x.x"
  public_ip       = "54.x.x.x"
```

### Step 4: Verify

```bash
# SSH into the server
ssh -i ~/.ssh/id_rsa ubuntu@$(terraform output -raw public_ip)

# Check Docker is running
docker ps

# Check application
curl http://localhost/auth/health
```

### Step 5: Destroy (cleanup)

```bash
terraform destroy
# Type 'yes' when prompted
```

---

## 7. User Data Script

The EC2 instance runs a startup script (`user_data`) that automatically:
1. Updates Ubuntu packages
2. Installs Docker and Docker Compose
3. Clones the application repository from GitHub
4. Runs `docker compose up -d --build`

This means the full stack is running within ~5 minutes of `terraform apply` completing — zero manual steps required.

---

## 8. Reproducibility

Terraform ensures full reproducibility:

| Property | How Achieved |
|----------|-------------|
| Same AMI every run | `data.aws_ami` with exact filters |
| Same configuration | Variables in `terraform.tfvars` |
| Idempotent | Re-running `apply` with no changes outputs "0 to change" |
| State tracked | `terraform.tfstate` records all deployed resources |
| Version-pinned provider | `~> 5.0` in `required_providers` |

---

## 9. Security Considerations

- AWS credentials stored in `terraform.tfvars` (gitignored, never committed)
- Root EBS volume is encrypted (`encrypted = true`)
- SSH CIDR can be restricted to your IP (`x.x.x.x/32`)
- Sensitive variables marked `sensitive = true` (not shown in plan output)

---

## 10. Cost Estimate (AWS us-east-1)

| Resource | Monthly Cost |
|----------|-------------|
| t3.medium EC2 | ~$30 |
| 30GB gp3 EBS | ~$2.40 |
| Elastic IP (when attached) | Free |
| Data transfer | ~$1 |
| **Total** | **~$33/month** |

Use `t3.micro` (free tier) for testing: change `instance_type = "t3.micro"` in `terraform.tfvars`.
