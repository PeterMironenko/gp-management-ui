# This is document describes PyQt5 UI for GP management Flask backend

## Installation on local host

**1. Prerequisites:**
- Windows 10 or higher, Linux, or macOS
- Python 3.8 or higher
- Git

**2. Clone the repository**
```bash
git clone https://github.com/PeterMironenko/gp-management.git
```
**3. Got to the project directory**

```bash
cd gp-management
```

**4. Create a virtual environment and activate it**
```bash
python3 -m venv .venv
```
Activate the virtual environment

***On Windows:***
```Powershell
.venv\Scripts\activate
```
***On Linux or macOS:***
```bash
source .venv/bin/activate
```
**5. Install the required dependencies**
```bash
pip install -r requirements.txt
```
Now you have successfully installed the required dependencies and you are ready to start the GUI application. Before starting the GUI application, you must decide either you want to run the local Flask backend for the purpose of the development and testing or you want to connect to the ready to use hosted Flask backend on http://home.paralleldynamic.com:5000. Please follow the instructions in the next sections accordingly. 

## Connecting GUI client to hosted Flask backend on http://home.paralleldynamic.com:5000

**1. Start the UI application**
```bash
python3 main.py
```
**2. Log into the system using admin credentials**
- URL: http://home.paralleldynamic.com:5000
- Username: admin
- Password: Ask Peter for the password

**3. Examine the "Admin Panel"**
In the "Admin Panel" there are several tabs: "User management", "Patient management", "Drug management", "Approval Required", "Patient Assignment". For more information about each tab functionality, please refer to the Design document.

**4. Open "User management" tab and update password for staff05 user**
- Double click on the "staff05" user record in the table
- In the opened form, in the fields "New Password" and "Confirm Password" enter the new password for the user and click "Update" button

**5. Log into the system using staff05 credentials**

Open a new terminal and run the same command as in step 6:

```bash
source .venv/bin/activate
python3 main.py
```
- In the login form, enter username "staff005" and the new password you set in step 3, and click "Login" button, the URL should remain the same http://home.paralleldynamic.com:5000.

**6. Examine the "Staff Dashboard"**
After successful login, you will be redirected to the "Staff Dashboard". Notice, in the top left conner there is Position and Name of the staff005 user, in my case this was "Nurse| Amelia Anderson" (yours might be different). In the "Staff Dashboard" there are two available Window tabs: "Appointments" and "Patients" For more information about each tab functionality, please refer to the Design document.


## Connecting GUI client to local Flask backend

**1. Start the Flask backend locally**

The source code of the GP management Flask backend is located in [GitHub repository](https://github.com/PeterMironenko/gp-management).
Follow the instructions in the README.md from "Installation on local host" section. 

**2. Start the UI application**
```bash
python3 main.py
```
**3. Log into the system using admin credentials**
- URL: http://localhost:5000
- Username: admin
- Password: Ask Peter for the password

**NOTE:** The URL for the local Flask backend execution is http://localhost:5000. It remains the same for all platforms Windows, Linux and macOS. If you are running the Flask backend on a different port, please update the URL in the "URL" field of the login form accordingly.

**NOTE:** Please change the default admin password after the first login for security reasons. You can do this in the "User management" tab in the "Admin Panel".

Perform the same steps as in the previous section "Connecting GUI client to hosted Flask backend" steps **4.**, **5.** and **6.** to examine the "Admin Panel" and "Staff Dashboard" functionality.



