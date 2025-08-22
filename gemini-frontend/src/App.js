// src/App.js
import React, { useState } from 'react';
import Login from './components/Login';
import FullAnalyzer from './components/FullAnalyzer';
import './App.css';

function App() {
  // Try to get the token from local storage on initial load
  const [vaultToken, setVaultToken] = useState(localStorage.getItem('vaultToken'));

  const handleLoginSuccess = (token) => {
    localStorage.setItem('vaultToken', token);
    setVaultToken(token);
  };

  const handleLogout = () => {
    localStorage.removeItem('vaultToken');
    setVaultToken(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Document Intelligence Platform</h1>
        {vaultToken && <button onClick={handleLogout} className="logout-button">Logout</button>}
      </header>
      <main>
        {!vaultToken ? (
          <Login onLoginSuccess={handleLoginSuccess} />
        ) : (
          <FullAnalyzer vaultToken={vaultToken} />
        )}
      </main>
    </div>
  );
}

export default App;