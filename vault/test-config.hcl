# correct-config.hcl

# A storage backend is required for Vault to start.
storage "file" {
  path = "C:/vault-data"
}

# Configure the listener.
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = "true"
}

# Enable the web UI.
ui = true