# Use the 'file' storage backend
storage "file" {
  # Path where Vault will store its encrypted data.
  # IMPORTANT: Use forward slashes (/) even on Windows.
  path = "C:/vault-data"
}

# Configure the server to listen on localhost, port 8200 over HTTP
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = "true" # Disables HTTPS for local development
}

# Enable the web UI
ui = true