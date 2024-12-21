# Bloodr - Blood and Organ Donation Management System

## Project Overview
Bloodr is a comprehensive web application designed to streamline the process of blood and organ donation. It connects donors with those in need through a user-friendly interface and efficient search system.

## Technology Stack
- **Backend**: Flask (Python 3.12)
- **Database**: MongoDB
- **Frontend**: Bootstrap 5, Custom CSS
- **Authentication**: Flask-Bcrypt
- **Additional Libraries**: PyMongo, Python-dotenv

## Key Features

### 1. User Authentication
- Secure registration and login system
- Password hashing with Bcrypt
- Session-based authentication
- First registered user becomes admin

### 2. User Management
- Comprehensive user profiles
- Role-based access control
- Admin dashboard for user management
- Profile updates and preferences

### 3. Donor Registration
#### Blood Donation
- Blood group selection (A+, A-, B+, B-, AB+, AB-, O+, O-)
- Donor status tracking
- City-based location

#### Organ Donation
- Multiple organ options:
  - Kidney
  - Liver
  - Heart
  - Corneas
  - Lungs
  - Pancreas

### 4. Search Functionality
- Search by donor type (blood/organ)
- Filter by blood group
- Filter by organ type
- City-based search
- Real-time results

### 5. Admin Features
- User management
- System statistics
- Donor tracking
- Access control

## Installation and Setup

### Prerequisites
```bash
- Python 3.12
- MongoDB
- Git (optional)
```

### Installation Steps
1. Clone the repository or download the source code
```bash
git clone [repository-url]
cd bloodr
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Start MongoDB service

4. Run the application
```bash
python app.py
```

5. Access the application at http://localhost:5000

## Project Structure
```
bloodr/
├── app.py                 # Main application file
├── requirements.txt       # Project dependencies
├── static/               # Static files
│   └── css/
│       └── style.css     # Custom styling
└── templates/            # HTML templates
    ├── about.html        # About page
    ├── admin.html        # Admin dashboard
    ├── base.html         # Base template
    ├── dashboard.html    # User dashboard
    ├── donate.html       # Donation preferences
    ├── find_donor.html   # Donor search
    ├── home.html         # Landing page
    ├── login.html        # Login form
    └── register.html     # Registration form
```

## Features in Detail

### 1. Homepage
- Welcome message
- Quick access to registration and login
- Information about blood and organ donation

### 2. User Registration
- Username
- Email address
- Phone number
- Address
- City
- Password (securely hashed)
- Blood donor status
- Organ donor status

### 3. User Dashboard
- Personal information
- Donation status
- Quick actions
- System statistics

### 4. Donor Search
- Advanced search filters
- Real-time results
- Contact options
- Location-based matching

### 5. Admin Dashboard
- User management
- System statistics
- Donor tracking
- Administrative controls

## Security Features
1. Password Hashing
2. Session Management
3. Form Validation
4. Admin Access Control
5. Secure Routes

## Database Schema

### Users Collection
```json
{
    "username": "string",
    "email": "string",
    "phone": "string",
    "address": "string",
    "city": "string",
    "password": "hashed_string",
    "blood_donor": "string",
    "blood_group": "string",
    "organ_donor": "string",
    "organ_group": "string",
    "is_admin": "boolean",
    "registration_date": "datetime"
}
```

### Donation Requests Collection
```json
{
    "donor_id": "ObjectId",
    "requester_id": "ObjectId",
    "type": "string",
    "status": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## Future Enhancements
1. Email Notifications
2. Real-time Chat
3. Mobile Application
4. Advanced Analytics
5. Geolocation Services
6. Automated Matching System

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- Flask Documentation
- MongoDB Documentation
- Bootstrap Team
- Font Awesome Icons
- Google Fonts

## Contact
For any queries or support, please contact [Your Contact Information]
