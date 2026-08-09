# Facial-Recognition-enabled-blockchain-based-voting-system
Facial-Recognition and OTP voting-system we have used customized blockchain
VoteSense
Python Version: 3.11.13

Project Explanation
VoteSense is a secure and modern online voting system. It incorporates facial recognition for voter verification to ensure authenticity and uses blockchain technology to maintain the integrity and transparency of election results. The system includes features for admin management of candidates and voters, and a user-friendly interface for casting votes and viewing results.

Installation
To set up and run VoteSense, follow these steps:

Clone the Repository:

git clone <repository_url>
cd VoteSense
Create a Virtual Environment (Recommended):

python -m venv venv
Activate the Virtual Environment:

On Windows:
.\venv\Scripts\activate
On macOS/Linux:
source venv/bin/activate
Install Dependencies: Install the required Python packages using pip:

pip install -r requirements.txt
Set up PostgreSQL Database: VoteSense uses PostgreSQL as its database.

Ensure you have PostgreSQL installed and running.
Create a database named voting_system.
Update the database connection string in app.py if your credentials differ from the default:
# ... existing code ...
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost:5432/voting_system' # REPLACE with your PostgreSQL credentials
# ... existing code ...
The default is postgresql://postgres:1234@localhost:5432/voting_system.
Initialize Database: Run the create_tables.py script to set up the database tables and create an initial admin user:

python create_tables.py
Note: This script will drop any existing tables before recreating them. Use with caution in production environments.

How to Run
After completing the installation, you can run the VoteSense application:

Ensure Virtual Environment is Active (if not already):

.\venv\Scripts\activate   # For Windows
# OR
source venv/bin/activate    # For macOS/Linux
Run the Application: The main.py script starts the Flask application.

python main.py
Access the Application: Open your web browser and navigate to http://127.0.0.1:5000 or http://localhost:5000.

Default Admin Credentials:

Username: admin
Password: admin123
Upon the first run, if no admin exists, a default admin account will be created automatically.
