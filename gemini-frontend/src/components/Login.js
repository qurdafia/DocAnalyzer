// src/components/Login.js
import React, { useState } from 'react';

function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    
    // Reads the Vault address from the .env.local file
    const VAULT_ADDR = process.env.REACT_APP_VAULT_ADDR || 'http://localhost:8200';
    
    try {
      const response = await fetch(`${VAULT_ADDR}/v1/auth/userpass/login/${username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.errors[0] || 'Login failed. Check username or password.');
      }
      
      // On success, Vault returns a client token.
      const clientToken = data.auth.client_token;
      onLoginSuccess(clientToken);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleLogin}>
        <h3>Application Login</h3>
        <p>Authenticate with Vault to continue.</p>
        <div className="form-group">
          <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" required />
        </div>
        <div className="form-group">
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" required />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
        {error && <p className="error-message">{error}</p>}
      </form>
    </div>
  );
}

export default Login;