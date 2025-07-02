import React, { useState } from 'react';
import './SignUp.css';

const COUNTRY_OPTIONS = [
  { code: '+91', label: 'India', flag: '🇮🇳' },
  { code: '+1', label: 'United States', flag: '🇺🇸' },
  { code: '+44', label: 'United Kingdom', flag: '🇬🇧' },
  { code: '+61', label: 'Australia', flag: '🇦🇺' },
  { code: '+1', label: 'Canada', flag: '🇨🇦' },
];        

function SignUp() {
  const [form, setForm] = useState({
    email: '',
    firstName: '',
    lastName: '',
    country: COUNTRY_OPTIONS[0].code,
    phone: '',
    password: '',
    terms: false,
    organization: '',
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
    if (!form.firstName) newErrors.firstName = 'First name is required.';
    if (!form.lastName) newErrors.lastName = 'Last name is required.';
    if (!form.phone) {
      newErrors.phone = 'Phone number is required.';
    } else if (!/^\d{6,15}$/.test(form.phone)) {
      newErrors.phone = 'Enter a valid phone number (6-15 digits, no country code).';
    }
    if (!form.password) {
      newErrors.password = 'Password is required.';
    } else if (form.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters.';
    }
    if (!form.terms) newErrors.terms = 'You must agree to the terms.';
    if (!form.organization) newErrors.organization = 'Organization is required.';
    if (!form.location) newErrors.location = 'Location is required.';
    return newErrors;
  };

  const handleChange = (e) => {
    const { id, value, type, checked, name } = e.target;
    if (name === 'country') {
      setForm((prev) => ({ ...prev, country: value }));
    } else {
      setForm((prev) => ({
        ...prev,
        [id === 'work-email' ? 'email' :
          id === 'first-name' ? 'firstName' :
          id === 'last-name' ? 'lastName' :
          id === 'phone-number' ? 'phone' :
          id === 'password' ? 'password' :
          id === 'terms' ? 'terms' :
          id === 'organization' ? 'organization' :
          id === 'location' ? 'location' : id]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length === 0) {
      // Submit form (e.g., send to backend)
      alert(`Account created successfully!\nPhone: ${form.country} ${form.phone}`);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-box">
        <div className="signup-header-row">
          <h2 className="signup-title">Create your account</h2>
          <span className="login-link">
            Already have an account? <a href="/login">Log in instead.</a>
          </span>
        </div>
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="work-email">Work email</label>
            <input
              type="email"
              id="work-email"
              value={form.email}
              onChange={handleChange}
              required
              autoComplete="email"
              className="line-input"
            />
            {errors.email && <div className="error-msg">{errors.email}</div>}
          </div>

          <div className="name-group">
            <div className="form-group">
              <label htmlFor="first-name">First name</label>
              <input
                type="text"
                id="first-name"
                value={form.firstName}
                onChange={handleChange}
                required
                autoComplete="given-name"
                className="line-input"
              />
              {errors.firstName && <div className="error-msg">{errors.firstName}</div>}
            </div>
            <div className="form-group">
              <label htmlFor="last-name">Last name</label>
              <input
                type="text"
                id="last-name"
                value={form.lastName}
                onChange={handleChange}
                required
                autoComplete="family-name"
                className="line-input"
              />
              {errors.lastName && <div className="error-msg">{errors.lastName}</div>}
            </div>
          </div>

          <div className="org-loc-group" style={{ display: 'flex', gap: 20 }}>
            <div className="form-group" style={{ width: '50%' }}>
              <label htmlFor="organization">Organization</label>
              <input
                type="text"
                id="organization"
                value={form.organization || ''}
                onChange={handleChange}
                required
                autoComplete="organization"
                className="line-input"
              />
              {errors.organization && <div className="error-msg">Organization is required.</div>}
            </div>
            <div className="form-group" style={{ width: '50%' }}>
              <label htmlFor="location">Location</label>
              <input
                type="text"
                id="location"
                value={form.location || ''}
                onChange={handleChange}
                required
                autoComplete="address-level2"
                className="line-input"
              />
              {errors.location && <div className="error-msg">Location is required.</div>}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="phone-number">Phone number <span style={{color: 'red'}}>*</span></label>
            <div className="phone-input">
              <select
                className="country-code"
                name="country"
                value={form.country}
                onChange={handleChange}
                required
              >
                {COUNTRY_OPTIONS.map((c) => (
                  <option key={c.code + c.label} value={c.code}>
                    {c.flag} {c.label} {c.code}
                  </option>
                ))}
              </select>
              <input
                type="tel"
                id="phone-number"
                value={form.phone}
                onChange={handleChange}
                autoComplete="tel"
                pattern="\d{6,15}"
                placeholder="Phone number"
                required
                className="line-input"
              />
            </div>
            {errors.phone && <div className="error-msg">{errors.phone}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password (min 8 characters)</label>
            <div className="password-input">
              <input
                type={passwordVisible ? "text" : "password"}
                id="password"
                value={form.password}
                onChange={handleChange}
                required
                autoComplete="new-password"
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

          <div className="form-group" style={{ width: '100%', padding: 0, margin: 0 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
              <input
                type="checkbox"
                id="terms"
                checked={form.terms}
                onChange={handleChange}
                required
                style={{ width: '22px', height: '22px', accentColor: '#0077ff', borderRadius: '6px', margin: 0, marginTop: '3px' }}
              />
              <label htmlFor="terms" style={{ marginLeft: '18px', fontSize: '1rem', fontWeight: 400, color: '#444', lineHeight: '1.6', wordBreak: 'break-word', textAlign: 'left', flex: 1 }}>
                By checking this box, I agree to receive updates, insights, and offers from Streamlineer and its affiliates by email and phone. I understand I can withdraw my consent.
              </label>
            </div>
          </div>
          {errors.terms && <div className="error-msg terms-error">{errors.terms}</div>}

          <button type="submit" className="create-account-btn">Create account</button>
        </form>

        <p className="terms-agreement">
          By creating an account you agree to Streamlineer's <a href="#">Terms & Conditions</a> and <a href="#">Privacy Policy</a>.
        </p>
      </div>
    </div>
  );
}

export default SignUp; 