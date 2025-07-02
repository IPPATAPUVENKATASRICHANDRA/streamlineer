import React, { useState } from 'react';
import '../SignUp/SignUp.css';
import { Link } from 'react-router-dom';

function Login() {
  const [form, setForm] = useState({
    email: '',
    password: '',
    organisation: '',
    location: '',
  });
  const [errors, setErrors] = useState({});
  const [passwordVisible, setPasswordVisible] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!form.email) {
      newErrors.email = 'Email is required.';
    } else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) {
      newErrors.email = 'Enter a valid email address.';
    }
    if (!form.password) {
      newErrors.password = 'Password is required.';
    }
    if (!form.organisation) newErrors.organisation = 'Organisation is required.';
    if (!form.location) newErrors.location = 'Location is required.';
    return newErrors;
  };

  const handleChange = (e) => {
    const { id, value } = e.target;
    setForm((prev) => ({ ...prev, [id]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length === 0) {
      // Submit login (e.g., send to backend)
      alert('Login successful!');
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2 className="login-title">Login to your account</h2>
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={form.email}
              onChange={handleChange}
              required
              autoComplete="email"
              className="line-input"
            />
            {errors.email && <div className="error-msg">{errors.email}</div>}
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1, marginRight: '8px' }}>
              <label htmlFor="organisation">Organisation</label>
              <input
                type="text"
                id="organisation"
                value={form.organisation}
                onChange={handleChange}
                required
                autoComplete="organization"
                className="line-input"
              />
              {errors.organisation && <div className="error-msg">{errors.organisation}</div>}
            </div>
            <div className="form-group" style={{ flex: 1, marginLeft: '8px' }}>
              <label htmlFor="location">Location</label>
              <input
                type="text"
                id="location"
                value={form.location}
                onChange={handleChange}
                required
                autoComplete="address-level2"
                className="line-input"
              />
              {errors.location && <div className="error-msg">{errors.location}</div>}
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input">
              <input
                type={passwordVisible ? "text" : "password"}
                id="password"
                value={form.password}
                onChange={handleChange}
                required
                autoComplete="current-password"
                className="line-input"
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setPasswordVisible(!passwordVisible)}
                tabIndex={-1}
              >
                <i className={passwordVisible ? "fas fa-eye-slash" : "fas fa-eye"}></i>
              </button>
            </div>
            {errors.password && <div className="error-msg">{errors.password}</div>}
          </div>
          <button type="submit" className="login-btn">LOGIN</button>
        </form>
        <p className="login-link">
          New to Streamlineer? <Link to="/signup">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export default Login; 