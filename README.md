# CatchMyRide WebApp

## Team Members:
- Aristaa Singh [sc23as2]
- Sinjini Sarkar [sc23ss2]
- Sreeja Tulluru [sc23sct]
- Adhiraj Kumar [sc23ak4]
- Aqeel Jindal [sc23aj2] 

## About The Project:

CatchMyRide is a web-based carpooling platform that allows users to book and offer rides for both commuting and one-time journeys.

During registration, users are able to act as both drivers and passengers from the same account! CatchMyRide promotes car-sharing and encourages users to explore the full range of services offered by the platform :)

Users can search for rides, negotiate pick-up points, and track their bookings. The system also supports features such as booking management, real-time chat with ride providers, and journey ratings, enhancing the overall user experience. Additionally, a Manager Portal is available to oversee the system, configure booking and platform fees, and monitor app revenue, including details of rides that have been published, booked, or cancelled.

> For a more detailed description of project features, usability, and user flows, please refer to [Home](https://github.com/COMP2913-24-25/software-engineering-project-team-19/wiki/) page in the GitHub Wiki.


## Main Features Of the Project 
- User registration and login (single account for both drivers and passengers)
- Publish a ride (as a driver) or book a ride (as a passenger)
- Search for rides based on:
  - Departure and arrival locations
  - Date and time
  - Ride category (one-time or commuting)
  - Price and available seats
- Real-time chat between drivers and passengers
- Live location tracking using OpenStreetMap (for both driver and passenger side)
- Booking management: passengers can cancel their booking at any time (with a booking fee penalty)
- Driver's dashboard: view weekly income statistics
- Manager portal for system management, revenue tracking, and customer support


## Tools and Framework
- Frontend: HTML, CSS, Bootstrap, JavaScript (for responsiveness and interactivity)
- Backend: Python Flask
- Database: SQLite
- Testing: Pytest and Coverage.py
- Deployment: Local Codespaces using setup scripts
- API tools - OpenStreetMap API for map integration and location services


## Technical Design Overview 
CatchMyRide follows a three-tier client-server architecture based on Python Flask for the backend and SQLite for persistent data storage.

Core database models include:
- User
- publish_ride
- book_ride
- Payment
- And others supporting user journeys and financial transactions.

> For a more detailed description of the Technical Design, please refer to [Technical Design and Data Modelling](https://github.com/COMP2913-24-25/software-engineering-project-team-19/wiki/Technical-Design-and-Data-Modelling) page in the Github Wiki.


## Project Setup Instructions

### User View Setup
- To get started with running this Flask webapp, the user needs to first set up a Python Flask environment. To make this easier, we have provided a simple script just for this purpose, which on being run:
  1. Removes any existing (or broken!) flask virtual environments in your codespace.  
  2. Creates a new python3 virtual environment 'flask' and installs Flask and all required dependencies automatically from requirements.txt.  

We found this a helpful approach to rebuilding potentially broken or problematic VMs, minimising the complexity of the entire process of setting up and running Flask.

To set up your Flask environment, run the following commands in the terminal:
```
  chmod +x setup_flask.sh   
  ./setup_flask.sh  
``` 

### Running Locally on Codespace
- Now that a functional virtual environment is ready, we can activate it with: `source flask/bin/activate`  
- And then simply run the app: `flask run`  


### Management View Setup
- To make the setup easier, we have already created a default Manager account in the database.  
You can log in using the following credentials:

  - **Username:** Manager
  - **Gmail:** Manager@gmail.com  
  - **Password:** manager@123

- However, if you want to create your own Manager account, follow these steps:  
  - You must first create a regular user account (it should already exist in the User table).
  - Activate your Flask environment (if not already activated), then promote the user to a Manager role by running the following command in the terminal:
```
  flask make-manager  
```
- You will be asked to enter the **email address** of the user you wish to promote.
- Enter the existing user's email. Once promoted, the user will have access to the **Management View** features.
- In case changes aren't immediately shown up while your webapp is running locally, it might be because Flask Debug mode is off and the changes made to the database are not reflected immediately. Try deactivating and re-activating flask, or just turning debug mode on. 

 
### Running the Tests
- To run the test files for the web application, we have set up an automated approach on Github actions where tests run automatically. However, if running the tests manually in the Codespace, use the following commands after setting up the Flask environment. 

To run all test files together:
```
  pytest tests/ 
``` 

To generate a coverage report:
```
  pytest --cov=app tests/ 
``` 
- Testing Strategy:
We employed unit testing and integration testing using Pytest.
The tests cover models, routes, form validations, and database operations.
Coverage reports were generated to measure the extent of code tested, targeting over 80% code coverage.

> For a more detailed description of the testing approach, please refer to [Testing Analysis](https://github.com/COMP2913-24-25/software-engineering-project-team-19/wiki/Testing-Analysis) page in the GitHub Wiki.


## Version Control and Git Workflow
- We used GitHub for version control, following a feature branch workflow.
- Almost every new feature was developed in a separate branch, with regular commits made throughout development.
- Pull requests were created for code reviews and merging into the main branch to maintain clean project history. This was mainly done when we wanted to close a feature on the Kanban Board. 


## Project Management and Issue Tracking
- Project management was handled through GitHub Issues and a Project Board (Kanban-style).
- Tasks, bugs, and milestones were created as issues, labeled appropriately, and assigned to team members.
- Progress was tracked through the board across different sprints, ensuring timely sprint planning and reviews.


## Accessibility Considerations
CatchMyRide was built with accessibility in mind:
- High-contrast color palettes and readable fonts were selected to meet WCAG 2.1 guidelines.
- Semantic HTML and ARIA attributes enhance screen reader compatibility.
- Keyboard navigation was tested extensively.
- Accessibility audits were conducted using WAVE tools.

> For a more detailed description of the Accessibility Considerations, please refer to [Accessibility](https://github.com/COMP2913-24-25/software-engineering-project-team-19/wiki/Accessibility) page in the GitHub Wiki.


## Known Issues and Limitations
- Live Location Access:  
  Users must ensure that location services are enabled on their browser/device, as live location tracking relies on browser geolocation APIs for both drivers and passengers.

- Same Port Requirement for Live Tracking:  
  This application requires that both the driver and passenger access the website from the *same server instance and port* for live location tracking to work correctly.  
  When testing locally, driver and passenger views should be opened in *different browsers* (e.g., Chrome for driver and Firefox for passenger) but must connect to the **same localhost:PORT address**.  
  This is necessary because live location data is maintained in-memory on the server, and cross-port communication is not currently supported.

- Driver Booking Their Own Ride:  
  The system currently allows a user to publish a ride as a driver and then book the same ride as a passenger.  
  While this action is technically possible, it is discouraged in normal usage.  
  To handle this scenario safely, the system is designed to always prioritize the *driver view* if the publishing user books their own ride.  
  This ensures that journey management and tracking behavior remains consistent.

- Manager Demotion Not Supported:    
  Once a user is promoted to a Manager role, there is currently no built-in feature to demote them back to a regular User through the web interface. If demotion is required, it must be handled manually by updating the database records directly.


[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/IsXyYN_x)
[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=18086283)