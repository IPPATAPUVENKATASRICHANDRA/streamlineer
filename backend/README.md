# Streamlineer Backend API

A Flask-based REST API with JWT authentication, Argon2 password hashing, and MongoDB Atlas integration.

## 🚀 Features

- **JWT Authentication** - Secure token-based authentication
- **Argon2 Password Hashing** - Industry-standard password security
- **MongoDB Atlas Integration** - Cloud database with connection pooling
- **Role-Based Access Control** - Inspector, IT, Manager roles
- **CORS Support** - Cross-origin resource sharing
- **Input Validation** - Marshmallow schema validation
- **Error Handling** - Comprehensive error responses
- **Logging** - Rotating file logs

## 📋 Prerequisites

- Python 3.8+
- MongoDB Atlas account
- Virtual environment (venv)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   cd streamlineer
   ```

2. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the `backend` directory:
   ```env
   # MongoDB Configuration
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/streamlineer
   
   # JWT Configuration
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
   JWT_ACCESS_TOKEN_EXPIRES=3600
   JWT_REFRESH_TOKEN_EXPIRES=604800
   
   # Flask Configuration
   FLASK_ENV=development
   FLASK_DEBUG=True
   SECRET_KEY=your-flask-secret-key-change-this-in-production
   
   # CORS Configuration
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   
   # Security Configuration
   PASSWORD_MIN_LENGTH=8
   MAX_LOGIN_ATTEMPTS=5
   ACCOUNT_LOCKOUT_DURATION=900
   ```

## 🗄️ MongoDB Atlas Setup

1. **Create MongoDB Atlas Account**
   - Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Sign up for a free account

2. **Create a Cluster**
   - Choose "Shared" (free tier)
   - Select cloud provider and region
   - Click "Create"

3. **Set up Database Access**
   - Go to "Database Access"
   - Click "Add New Database User"
   - Create username and password
   - Select "Read and write to any database"
   - Click "Add User"

4. **Set up Network Access**
   - Go to "Network Access"
   - Click "Add IP Address"
   - Click "Allow Access from Anywhere" (for development)
   - Click "Confirm"

5. **Get Connection String**
   - Go to "Database"
   - Click "Connect"
   - Choose "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Replace `<dbname>` with `streamlineer`

## 🏃‍♂️ Running the Application

1. **Start the server**
   ```bash
   cd backend
   python run.py
   ```

2. **The API will be available at:**
   - `http://localhost:5000`

3. **Health check:**
   - `GET http://localhost:5000/health`

## 📚 API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "organization": "Tech Corp",
  "location": "New York",
  "phone": "1234567890",
  "country_code": "+1",
  "password": "MyPassword123",
  "role": "inspector",
  "terms": true
}
```

#### Login User
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "MyPassword123",
  "organization": "Tech Corp",
  "location": "New York"
}
```

#### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer your-access-token
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer your-access-token
```

## 🔐 Authentication

### JWT Token Structure

**Access Token Payload:**
```json
{
  "user_id": "user_id",
  "email": "user@example.com",
  "role": "inspector",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Refresh Token Payload:**
```json
{
  "user_id": "user_id",
  "email": "user@example.com",
  "type": "refresh",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Using Tokens

Include the access token in the Authorization header:
```http
Authorization: Bearer your-access-token
```

## 👥 User Roles

- **inspector** - Can perform inspections
- **it** - IT support and system management
- **manager** - Administrative access

## 🔒 Security Features

- **Password Requirements:**
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number

- **Account Lockout:**
  - 5 failed login attempts
  - 15-minute lockout period

- **Token Security:**
  - Access tokens expire in 1 hour
  - Refresh tokens expire in 7 days
  - Cryptographically signed

## 📊 Database Schema

### Users Collection
```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "organization": "Tech Corp",
  "location": "New York",
  "phone": "1234567890",
  "country_code": "+1",
  "password_hash": "argon2-hash",
  "role": "inspector",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "email_verified": false,
  "last_login": "2024-01-15T10:30:00Z",
  "login_attempts": 0,
  "account_locked": false,
  "lockout_until": null
}
```

## 🧪 Testing

### Test Registration
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "firstName": "Test",
    "lastName": "User",
    "organization": "Test Corp",
    "location": "Test City",
    "phone": "1234567890",
    "country_code": "+1",
    "password": "TestPass123",
    "role": "inspector",
    "terms": true
  }'
```

### Test Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "organization": "Test Corp",
    "location": "Test City"
  }'
```

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check your MongoDB Atlas connection string
   - Ensure network access allows your IP
   - Verify database user credentials

2. **JWT Token Issues**
   - Check JWT_SECRET_KEY in .env file
   - Ensure tokens are not expired
   - Verify token format in Authorization header

3. **CORS Errors**
   - Check CORS_ORIGINS in .env file
   - Ensure frontend URL is included

4. **Password Validation Errors**
   - Ensure password meets requirements
   - Check password length and complexity

## 📝 Logs

Logs are stored in `backend/logs/streamlineer.log` with rotating file handler.

## 🔄 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token expiry (seconds) | 3600 |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token expiry (seconds) | 604800 |
| `FLASK_ENV` | Flask environment | development |
| `FLASK_DEBUG` | Debug mode | True |
| `SECRET_KEY` | Flask secret key | Required |
| `CORS_ORIGINS` | Allowed CORS origins | localhost:3000 |
| `PASSWORD_MIN_LENGTH` | Minimum password length | 8 |
| `MAX_LOGIN_ATTEMPTS` | Max failed login attempts | 5 |
| `ACCOUNT_LOCKOUT_DURATION` | Lockout duration (seconds) | 900 |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. 