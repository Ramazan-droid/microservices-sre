output "instance_id" {
  description = "Compute Engine instance ID"
  value       = google_compute_instance.microservices_server.id
}

output "public_ip" {
  description = "External IP address of the server"
  value       = google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip
}

output "public_dns" {
  description = "Instance public DNS name"
  value       = google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip
}

output "frontend_url" {
  description = "Application frontend URL"
  value       = "http://${google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip}"
}

output "grafana_url" {
  description = "Grafana dashboard URL"
  value       = "http://${google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://${google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip}:9090"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/id_rsa ubuntu@${google_compute_instance.microservices_server.network_interface[0].access_config[0].nat_ip}"
}

output "firewall_rule_id" {
  description = "Firewall rule ID (GCP equivalent of security group)"
  value       = google_compute_firewall.microservices_sg.id
}