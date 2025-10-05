# 🏔️ Snowflake Database Setup Guide

This guide will help you set up Snowflake as the database for the AI Agent Chat application.

## 📋 Prerequisites

1. **Snowflake Account**: You need an active Snowflake account
2. **Python Environment**: Python 3.8+ with pip
3. **Required Packages**: Snowflake connector and dependencies

## 🚀 Quick Setup

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Get Snowflake Credentials**

#### **From Snowflake Web Interface:**
1. Log into your Snowflake account
2. Go to **Admin** → **Users & Roles**
3. Create a new user or use existing user
4. Note down the following information:
   - **Username**: Your Snowflake username
   - **Password**: Your Snowflake password
   - **Account**: Your account identifier (e.g., `abc12345.us-east-1`)
   - **Warehouse**: Default warehouse name (e.g., `COMPUTE_WH`)
   - **Database**: Database name (e.g., `AI_AGENT_SCHEDULER`)
   - **Schema**: Schema name (e.g., `PUBLIC`)
   - **Role**: User role (e.g., `ACCOUNTADMIN`)

#### **From Snowflake SQL:**
```sql
-- Check your current account
SELECT CURRENT_ACCOUNT();

-- Check your current user
SELECT CURRENT_USER();

-- Check your current role
SELECT CURRENT_ROLE();

-- Check your current warehouse
SELECT CURRENT_WAREHOUSE();

-- Check your current database
SELECT CURRENT_DATABASE();

-- Check your current schema
SELECT CURRENT_SCHEMA();
```

### **3. Configure Environment Variables**

Create a `.env` file in your project root:

```env
# Snowflake Database Configuration
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=AI_AGENT_SCHEDULER
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# AI Agent Configuration
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here

# Optional - Canvas integration
CANVAS_API_URL=https://your-canvas-instance.instructure.com/api/v1
CANVAS_API_TOKEN=your_canvas_token_here

# Optional - Google Calendar
GOOGLE_CREDENTIALS_FILE=credentials.json

# Application Settings
DEBUG=False
PORT=8501
```

### **4. Create Database and Schema**

#### **Option A: Using Snowflake Web Interface**
1. Log into Snowflake
2. Go to **Data** → **Databases**
3. Click **Create Database**
4. Name: `AI_AGENT_SCHEDULER`
5. Click **Create**

#### **Option B: Using SQL**
```sql
-- Create database
CREATE DATABASE IF NOT EXISTS AI_AGENT_SCHEDULER;

-- Use the database
USE DATABASE AI_AGENT_SCHEDULER;

-- Create schema (optional, PUBLIC is default)
CREATE SCHEMA IF NOT EXISTS PUBLIC;

-- Use the schema
USE SCHEMA PUBLIC;
```

### **5. Set Up Tables**

Run the database setup script:
```bash
python database_setup.py
```

Or manually create tables in Snowflake:
```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    last_login TIMESTAMP_NTZ,
    is_active BOOLEAN DEFAULT TRUE
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_name VARCHAR(100) DEFAULT 'New Chat',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'agent')),
    agent_name VARCHAR(50),
    content TEXT NOT NULL,
    timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR(20) DEFAULT 'sent',
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Agent status table
CREATE TABLE IF NOT EXISTS agent_status (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    last_update TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### **6. Test Connection**

Test your Snowflake connection:
```bash
python -c "
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
        role=os.getenv('SNOWFLAKE_ROLE')
    )
    print('✅ Snowflake connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

## 🔧 Configuration Details

### **Snowflake Connection Parameters**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `SNOWFLAKE_USER` | Your Snowflake username | `john_doe` |
| `SNOWFLAKE_PASSWORD` | Your Snowflake password | `secure_password123` |
| `SNOWFLAKE_ACCOUNT` | Your account identifier | `abc12345.us-east-1` |
| `SNOWFLAKE_WAREHOUSE` | Warehouse name | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | Database name | `AI_AGENT_SCHEDULER` |
| `SNOWFLAKE_SCHEMA` | Schema name | `PUBLIC` |
| `SNOWFLAKE_ROLE` | User role | `ACCOUNTADMIN` |

### **Account Identifier Format**
Your account identifier can be found in several formats:
- **Full URL**: `https://abc12345.us-east-1.snowflakecomputing.com`
- **Account ID**: `abc12345.us-east-1`
- **Short Account**: `abc12345` (if in default region)

### **Warehouse Configuration**
Make sure your warehouse is:
- **Running**: Not suspended
- **Accessible**: Your role has access
- **Properly sized**: For your workload

## 🚀 Running the Application

### **Start the Application**
```bash
python run_imessage.py
```

### **Alternative: Direct Streamlit**
```bash
streamlit run streamlit_imessage_enhanced.py
```

## 🔍 Troubleshooting

### **Common Issues**

1. **Connection Failed**
   ```
   Error: 250001 (08001): None: Failed to connect to DB
   ```
   - Check your account identifier
   - Verify username and password
   - Ensure warehouse is running

2. **Authentication Failed**
   ```
   Error: 390100 (08001): None: Authentication failed
   ```
   - Check username and password
   - Verify account identifier
   - Ensure user exists and is active

3. **Database Not Found**
   ```
   Error: 2003 (08001): None: Database 'AI_AGENT_SCHEDULER' not found
   ```
   - Create the database in Snowflake
   - Check database name in .env file
   - Verify you have access to the database

4. **Warehouse Not Found**
   ```
   Error: 2003 (08001): None: Warehouse 'COMPUTE_WH' not found
   ```
   - Check warehouse name
   - Ensure warehouse exists
   - Verify your role has access

5. **Permission Denied**
   ```
   Error: 390100 (08001): None: Access denied
   ```
   - Check your role permissions
   - Ensure you have CREATE TABLE privileges
   - Verify database and schema access

### **Debug Mode**
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### **Connection Testing**
Test individual components:
```python
# Test basic connection
import snowflake.connector
conn = snowflake.connector.connect(
    user='your_username',
    password='your_password',
    account='your_account'
)
print("✅ Basic connection successful")

# Test with full parameters
conn = snowflake.connector.connect(
    user='your_username',
    password='your_password',
    account='your_account',
    warehouse='COMPUTE_WH',
    database='AI_AGENT_SCHEDULER',
    schema='PUBLIC'
)
print("✅ Full connection successful")
```

## 📊 Performance Optimization

### **Warehouse Sizing**
- **X-Small**: For development and testing
- **Small**: For light production use
- **Medium**: For moderate workloads
- **Large**: For heavy production use

### **Query Optimization**
- Use appropriate indexes
- Optimize query patterns
- Monitor query performance
- Use query profiling

### **Cost Management**
- Suspend warehouse when not in use
- Monitor credit consumption
- Use auto-suspend settings
- Optimize query performance

## 🔒 Security Best Practices

### **Credential Management**
- Use environment variables
- Never hardcode credentials
- Use key management services
- Rotate passwords regularly

### **Access Control**
- Use least privilege principle
- Create dedicated service accounts
- Monitor access logs
- Implement role-based access

### **Data Protection**
- Enable encryption at rest
- Use secure connections
- Implement data masking
- Monitor data access

## 📈 Monitoring and Maintenance

### **Monitoring Queries**
```sql
-- Check warehouse usage
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY;

-- Check query history
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY;

-- Check storage usage
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE;
```

### **Maintenance Tasks**
- Monitor warehouse usage
- Check query performance
- Review access logs
- Update security settings

## 🆘 Support

For additional help:
1. Check Snowflake documentation
2. Review error messages carefully
3. Test connection parameters
4. Verify permissions and access
5. Contact Snowflake support if needed

---

**🏔️ Your Snowflake database is now ready for the AI Agent Chat application!**
