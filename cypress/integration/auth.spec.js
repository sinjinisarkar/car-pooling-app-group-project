// cypress/integration/auth.spec.js

describe('Authentication Tests', () => {
  
    // Before each test, visit the base URL
    beforeEach(() => {
      cy.visit('/'); // Replace with the actual URL of your app
    });
  
    it('should validate password strength on sign-up', () => {
      // Visit the signup page
      cy.visit('/signup'); // Adjust according to your actual signup URL
  
      // Try submitting the form with a weak password
      cy.get('#signup-password').type('weak');
      cy.get('#signupConfirmPassword').type('weak');
      cy.get('#signupForm').submit();
      
      // Check for password validation alert
      cy.on('window:alert', (alertText) => {
        expect(alertText).to.contains('Password must be at least 8 characters long with at least one special character.');
      });
    });
  
    it('should show password mismatch alert on sign-up', () => {
      // Visit the signup page
      cy.visit('/signup');
  
      // Type in non-matching passwords
      cy.get('#signup-password').type('Password@123');
      cy.get('#signupConfirmPassword').type('DifferentPassword@123');
      cy.get('#signupForm').submit();
  
      // Check for password mismatch alert
      cy.on('window:alert', (alertText) => {
        expect(alertText).to.contains('Passwords do not match.');
      });
    });
  
    it('should register a new user successfully', () => {
      // Visit the signup page
      cy.visit('/signup');
  
      // Fill in the form and submit it
      cy.get('#signup-name').type('testuser');
      cy.get('#signup-email').type('testuser@example.com');
      cy.get('#signup-password').type('Password@123');
      cy.get('#signupConfirmPassword').type('Password@123');
      cy.get('#signupForm').submit();
  
      // Check for successful registration and login modal
      cy.get('#signupModal').should('not.be.visible');
      cy.get('#loginModal').should('be.visible');
    });
  
    it('should log in an existing user successfully', () => {
      // Visit the login page
      cy.visit('/login');
  
      // Fill in the login form
      cy.get('#login-email').type('testuser@example.com');
      cy.get('#login-password').type('Password@123');
      cy.get('#loginForm').submit();
  
      // Check for successful login (e.g., redirection)
      cy.url().should('not.include', '/login'); // Check if the URL changed after login
      cy.contains('Logout').should('be.visible'); // Check if the logout button is visible
    });
  
    it('should show alert if login fails', () => {
      // Visit the login page
      cy.visit('/login');
  
      // Try logging in with incorrect credentials
      cy.get('#login-email').type('wronguser@example.com');
      cy.get('#login-password').type('WrongPassword@123');
      cy.get('#loginForm').submit();
  
      // Check for login failure alert
      cy.on('window:alert', (alertText) => {
        expect(alertText).to.contains('Login failed.');
      });
    });
  
    it('should log out successfully', () => {
      // Log in first
      cy.visit('/login');
      cy.get('#login-email').type('testuser@example.com');
      cy.get('#login-password').type('Password@123');
      cy.get('#loginForm').submit();
  
      // Click the logout button
      cy.get('#logout-form').click();
  
      // Check if the user is logged out
      cy.url().should('include', '/');
      cy.contains('Login').should('be.visible');
    });
  
    it('should toggle password visibility when clicking the eye icon', () => {
      // Visit the signup page
      cy.visit('/signup');
  
      // Get the password input field and eye icon
      const passwordField = cy.get('#signup-password');
      const toggleIcon = cy.get('#toggle-password-icon');
  
      // Check if the password is initially hidden
      passwordField.should('have.attr', 'type', 'password');
  
      // Click the toggle icon to reveal the password
      toggleIcon.click();
      passwordField.should('have.attr', 'type', 'text');
  
      // Click the toggle icon again to hide the password
      toggleIcon.click();
      passwordField.should('have.attr', 'type', 'password');
    });
  });
  