/**
 * Login Page (Placeholder)
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Placeholder authentication - in production would call auth API
    if (email && password) {
      // Store placeholder token
      localStorage.setItem('auth_token', 'placeholder_token');
      navigate('/cases');
    } else {
      setError('Please enter email and password');
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>X-Tern Agents</h1>
        <h2>Sign In</h2>
        
        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
          
          <button type="submit" className="btn-primary">
            Sign In
          </button>
        </form>
        
        <p className="placeholder-notice">
          This is a placeholder login. Enter any credentials to continue.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
