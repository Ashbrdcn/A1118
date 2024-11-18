from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for flash messages; set to a secure random key in production

# Database connection function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='ecomDB',
            user='root',
            password=''
        )
        if conn.is_connected():
            print("Database connected successfully.")
        return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

# Route to check if the database connection works
@app.route('/check_connection', methods=['GET'])
def check_connection():
    conn = get_db_connection()
    if conn:
        conn.close()  # Close connection after checking
        return jsonify({"message": "Connection successful"})
    else:
        return jsonify({"message": "Connection failed"}), 500

# Login required decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to access this page", category="danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__  # Ensure the original function name is preserved
    return wrapper


@app.route('/', methods=['GET'])
def home():
     # Assuming user information is stored in session after login
    user = session.get('user')  # Retrieve user data from session
    is_approved = user.get('is_approved', False) if user else False  # Check if user is approved
    
    return render_template('home.html', is_approved=is_approved)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error")
            return redirect(url_for('login'))
        
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            # Validate required fields
            if not email or not password:
                flash("Both email and password are required")
                return redirect(url_for('login'))

            cursor = conn.cursor()

            # Fetch the user data
            query = "SELECT id, password, role FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()

            if user:
                # Check if the password matches
                if user[1] == password:  # Compare plain text passwords directly
                    session['user_id'] = user[0]  # Store user ID in session
                    session['role'] = user[2]  # Store role in session
                    role = user[2]

                    # Check if the user is an approved seller
                    cursor.execute("SELECT status FROM sellers WHERE user_id = %s", (user[0],))
                    seller_status = cursor.fetchone()
                    session['is_seller'] = seller_status and seller_status[0] == 'approve'

                    # Redirect based on user role
                    if role == 'admin':
                        return redirect(url_for('admin_page'))
                    elif role == 'superadmin':
                        return redirect(url_for('super_page'))
                    elif role == 'user':
                        return redirect(url_for('user_page'))
                    else:
                        flash("Unknown role encountered", category="danger")
                        return redirect(url_for('login'))
                else:
                    flash("Invalid email or password", category="danger")
                    return redirect(url_for('login'))
            else:
                flash("Invalid email or password", category="danger")
                return redirect(url_for('login'))

        except Error as e:
            print(f"Login error: {e}")
            flash("An internal database error occurred", category="danger")
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Failed to connect to the database")
            return redirect(url_for('signup'))

        try:
            email = request.form.get('email')
            password = request.form.get('password')
            role = 'user'  # Default role is 'user'

            # Validate required fields
            if not email or not password:
                flash("Email and password are required")
                return redirect(url_for('signup'))

            cursor = conn.cursor()

            # Insert the user into the 'users' table
            query = "INSERT INTO users (email, password, role) VALUES (%s, %s, %s)"
            cursor.execute(query, (email, password, role))  # Store plain text password
            conn.commit()
            flash("User registered successfully!")  # Success message
            return redirect(url_for('login'))  # Redirect to login after successful signup

        except Error as e:
            print(f"Error while inserting user data: {e}")
            flash("Failed to register user", category="danger")
            return redirect(url_for('signup'))
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    return render_template('signup.html')

from flask import session  # Ensure you have session imported

from flask import session  # Ensure you have session imported

@app.route('/seller_registration', methods=['GET', 'POST'])
def seller_registration():
    if request.method == 'POST':
        conn = get_db_connection()
        if conn is None:
            flash("Failed to connect to the database", "danger")
            return redirect(url_for('seller_registration'))

        # Get user_id from session (assuming the user is logged in and their ID is stored in session)
        user_id = session.get('user_id')
        if not user_id:
            flash("User ID not found in session", "danger")
            return redirect(url_for('seller_registration'))

        try:
            cursor = conn.cursor()
            # Check if user already has a seller application
            check_query = "SELECT status FROM sellers WHERE user_id = %s"
            cursor.execute(check_query, (user_id,))
            existing_application = cursor.fetchone()

            if existing_application:
                flash("You have already applied to be a seller.")
                return redirect(url_for('home'))  # Redirect to homepage if application exists

            # Get form data
            first_name = request.form.get('firstName')
            last_name = request.form.get('lastName')
            email = request.form.get('email')
            phone_number = request.form.get('phoneNumber')
            address = request.form.get('address')
            postal_code = request.form.get('postalCode')
            business_name = request.form.get('businessName')
            description = request.form.get('description')

            # Validate required fields
            if not first_name or not last_name or not email or not business_name:
                flash("First name, last name, email, and business name are required", "danger")
                return redirect(url_for('seller_registration'))

            # Insert data into the 'sellers' table
            insert_query = """
                INSERT INTO sellers (user_id, first_name, last_name, email, phone_number, address, postal_code, business_name, description, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
            """
            cursor.execute(insert_query, (user_id, first_name, last_name, email, phone_number, address, postal_code, business_name, description))
            conn.commit()
            flash("Your application has been submitted for approval.", "success")
            return redirect(url_for('home'))

        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
            return redirect(url_for('seller_registration'))
        finally:
            if conn:
                conn.close()  # Ensure connection is closed

    return render_template('seller_registration.html')

@app.route('/notifications')
@login_required
def notifications():
    user_id = session.get('user_id')
    conn = get_db_connection()
    if conn is None:
        flash("Database connection error", category="danger")
        return redirect(url_for('home'))

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        notifications = cursor.fetchall()
        
        # Mark all notifications as read
        update_query = "UPDATE notifications SET is_read = TRUE WHERE user_id = %s"
        cursor.execute(update_query, (user_id,))
        conn.commit()

        return render_template('notifications.html', notifications=notifications)

    except Error as e:
        print(f"Error fetching notifications: {e}")
        flash("Failed to fetch notifications.", category="danger")
        return redirect(url_for('home'))
    
    finally:
        if conn:
            conn.close()


def create_notification(user_id, message):
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to the database for notification.")
        return False

    try:
        cursor = conn.cursor()
        query = "INSERT INTO notifications (user_id, message) VALUES (%s, %s)"
        cursor.execute(query, (user_id, message))
        conn.commit()
        return True  # Notification created successfully
    except Error as e:
        print(f"Error creating notification: {e}")
        return False
    finally:
        if conn:
            conn.close()

@app.route('/admin_page', methods=['GET'])
@login_required
def admin_page():
    if session.get('role') != 'admin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    return render_template('admin_page.html')

@app.route('/view-user', methods=['GET'])
@login_required
def view_user():
    if session.get('role') != 'admin':  # Restrict access to admin
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    # Fetch users from the database or render the user viewing template
    return render_template('view_user.html')  # Replace with your template

@app.route('/view-seller', methods=['GET'])
@login_required
def view_seller():
    if session.get('role') != 'admin':  # Restrict access to admin
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    # Fetch sellers from the database or render the seller viewing template
    return render_template('view_seller.html')  # Replace with your template

@app.route('/admin_logout')
def admin_logout():
    session.clear()  # Clear the session on logout
    flash("Logged out successfully!", category="success")  # Flash message on successful logout
    return redirect(url_for('login'))  # Redirect to the login page after logout


@app.route('/super_page', methods=['GET'])
@login_required
def super_page():
    if session.get('role') != 'superadmin':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    return render_template('super_page.html')

@app.route('/user_page', methods=['GET'])
@login_required
def user_page():
    if session.get('role') != 'user':
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    return render_template('user_page.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear the session on logout
    flash("Logged out successfully!", category="success")
    return redirect(url_for('login'))

@app.route('/viewseller_application')
def viewseller_application():
    # Establishing the connection to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Query to fetch relevant fields from the 'sellers' table
        cursor.execute("""
            SELECT id, user_id first_name, last_name, email, phone_number, address, postal_code, business_name, description, created_at, status 
            FROM sellers
        """)
        sellers = cursor.fetchall()  # Fetch all the seller records

    except Exception as e:
        print(f"Error fetching sellers data: {e}")
        sellers = []  # If there is an error, return an empty list

    finally:
        cursor.close()
        conn.close()  # Close the database connection

    sidebarAdminSide = "sidebarAdminSide.html"  # Define sidebar template

    # Render the template, passing the sellers data and sidebar HTML
    return render_template('viewseller_application.html', sellers=sellers, sidebar=sidebarAdminSide)


@app.route('/approve_seller/<int:id>', methods=['POST'])
@login_required
def approve_seller(id):
    if session.get('role') != 'admin':  # Restrict access to admin
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    if conn is None:
        flash("Failed to connect to the database", category="danger")
        return redirect(url_for('viewseller_application'))
    
    try:
        cursor = conn.cursor()
        
        # Update the seller's status to "approve" with the correct column name
        query = "UPDATE sellers SET status = 'approve' WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()  # Commit the change to the database
        
        # Fetch user ID associated with the seller to send notification
        cursor.execute("SELECT user_id FROM sellers WHERE id = %s", (id,))
        user_id = cursor.fetchone()[0]  # Fetch the user_id

        # Create a notification for the user
        if create_notification(user_id, "Your seller application has been approved"):
            flash("Seller has been approved and notified.", category="success")
        else:
            flash("Seller approved, but failed to send notification.", category="warning")

        return redirect(url_for('viewseller_application'))  # Redirect back to the seller applications page

    except Error as e:
        print(f"Error while approving seller: {e}")
        flash("Failed to approve seller.", category="danger")
        return redirect(url_for('viewseller_application'))
    
    finally:
        if conn:
            conn.close()  # Ensure connection is closed



@app.route('/decline_seller/<int:id>', methods=['POST'])
@login_required
def decline_seller(id):
    if session.get('role') != 'admin':  # Restrict access to admin
        flash("Access restricted", category="danger")
        return redirect(url_for('home'))
    
    # Establish database connection
    conn = get_db_connection()
    if conn is None:
        flash("Failed to connect to the database", category="danger")
        return redirect(url_for('viewseller_application'))
    
    try:
        cursor = conn.cursor()

        # Update the seller's status to "declined"
        query = "UPDATE sellers SET status = 'Declined' WHERE id = %s"
        cursor.execute(query, (id,))
        conn.commit()  # Commit the change to the database

        flash("Seller declined successfully!", category="danger")
        return redirect(url_for('viewseller_application'))  # Redirect back to the seller applications page
    
    except Error as e:
        flash(f"Error: {e}", category="danger")
        return redirect(url_for('viewseller_application'))
    
    finally:
        if conn:
            conn.close()  # Ensure connection is closed

if __name__ == '__main__':
    app.run(debug=True)  # Optional: Set debug=True for helpful error messages
