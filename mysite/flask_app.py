import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialisiere das Flask-App und LoginManager
app = Flask(__name__)
app.secret_key = 'dein_geheimer_schlüssel'

login_manager = LoginManager()
login_manager.init_app(app)

# MySQL-Verbindungsdetails
db_config = {
    'host': 'Elias.mysql.pythonanywhere-services.com',
    'user': 'Elias',
    'password': 'Merkbardenki25',
    'database': 'Elias$Rezepte'
}

# Datenbankverbindung
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Fehler bei der Verbindung zur Datenbank: {err}")
        return None

# Flask-Login User Klasse
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# Flask-Login: Benutzer laden
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None  # Keine Verbindung zur Datenbank
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[3])  # ID, Username, Role
    return None

# Route für die Startseite (Index)
@app.route('/')
def index():
    return render_template('index.html')

# Route für die Registrierung
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']  # E-Mail hinzufügen
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            flash("Fehler bei der Verbindung zur Datenbank.", 'danger')
            return redirect(url_for('register'))

        cursor = conn.cursor()

        try:
            # Überprüfen, ob der Benutzername bereits existiert
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Benutzername bereits vergeben!', 'danger')
                return redirect(url_for('register'))

            # Überprüfen, ob die E-Mail-Adresse bereits vergeben ist
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_email = cursor.fetchone()

            if existing_email:
                flash('E-Mail-Adresse bereits vergeben!', 'danger')
                return redirect(url_for('register'))

            # Passwort hashen
            password_hash = generate_password_hash(password)

            # Neuen Benutzer in die Datenbank einfügen (einschließlich der E-Mail)
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                           (username, password_hash, email, role))
            conn.commit()
            flash('Benutzer erfolgreich registriert! Bitte logge dich ein.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Fehler bei der Registrierung: {str(e)}', 'danger')
            conn.rollback()  # Falls ein Fehler auftritt, wird die Transaktion zurückgesetzt
        finally:
            conn.close()

    return render_template('register.html')


# Route für das Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        if not conn:
            flash("Fehler bei der Verbindung zur Datenbank.", 'danger')
            return redirect(url_for('login'))

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            # Passwort überprüfen
            if check_password_hash(user_data[2], password):  # UserData[2] ist das Passwort
                user = User(user_data[0], user_data[1], user_data[3])
                login_user(user)

                # Weiterleitung zur Rollenauswahl
                return redirect(url_for('role_selection'))
            else:
                flash('Ungültiges Passwort!', 'danger')
        else:
            flash('Benutzername nicht gefunden!', 'danger')

    return render_template('login.html')

# Route zur Rollenauswahl
@app.route('/role_selection')
@login_required
def role_selection():
    if current_user.role == 'Rezepteverwalter':
        return redirect(url_for('add_recipe'))  # Weiterleitung zu Rezeptverwaltung
    elif current_user.role == 'Koch':
        return redirect(url_for('recipes'))  # Weiterleitung zu Rezeptanzeige
    return redirect(url_for('login'))

# Route zum Anzeigen der Rezepte
@app.route('/recipes')
@login_required
def recipes():
    conn = get_db_connection()
    if not conn:
        flash("Fehler bei der Verbindung zur Datenbank.", 'danger')
        return redirect(url_for('login'))
    cursor = conn.cursor()
    # Abfrage für Rezepte und deren Nährwerte
    cursor.execute("""
        SELECT r.id, r.name, r.zutaten, r.zubereitung, n.kalorien, n.protein, n.kohlenhydrate, n.fett, n.ballaststoffe
        FROM rezepte r
        LEFT JOIN naehrwerte n ON r.id = n.rezept_id
    """)
    recipes = cursor.fetchall()
    conn.close()

    return render_template('recipes.html', recipes=recipes)

# Route zum Hinzufügen von Rezepten (nur für Rezeptverwalter)
@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if current_user.role != 'Rezepteverwalter':
        flash('Du hast keine Berechtigung, neue Rezepte hinzuzufügen.', 'danger')
        return redirect(url_for('recipes'))

    if request.method == 'POST':
        name = request.form['name']
        zutaten = request.form['zutaten']
        zubereitung = request.form['zubereitung']
        kalorien = request.form['kalorien']
        protein = request.form['protein']
        kohlenhydrate = request.form['kohlenhydrate']
        fett = request.form['fett']
        ballaststoffe = request.form['ballaststoffe']

        conn = get_db_connection()
        if not conn:
            flash("Fehler bei der Verbindung zur Datenbank.", 'danger')
            return redirect(url_for('add_recipe'))

        cursor = conn.cursor()

        try:
            # Rezept in die "rezepte"-Tabelle einfügen
            cursor.execute("INSERT INTO rezepte (name, zutaten, zubereitung) VALUES (%s, %s, %s)",
                           (name, zutaten, zubereitung))
            conn.commit()

            # Rezept-ID ermitteln
            rezept_id = cursor.lastrowid

            # Nährwerte in die "naehrwerte"-Tabelle einfügen
            cursor.execute("INSERT INTO naehrwerte (rezept_id, kalorien, protein, kohlenhydrate, fett, ballaststoffe) VALUES (%s, %s, %s, %s, %s, %s)",
                           (rezept_id, kalorien, protein, kohlenhydrate, fett, ballaststoffe))
            conn.commit()

            flash('Rezept erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('recipes'))
        except Exception as e:
            flash(f'Fehler beim Hinzufügen des Rezepts: {str(e)}', 'danger')
            conn.rollback()  # Falls ein Fehler auftritt, wird die Transaktion zurückgesetzt
        finally:
            conn.close()

    return render_template('add_recipe.html')

# Route zum Löschen von Rezepten (nur für Rezeptverwalter)
@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    if current_user.role != 'Rezepteverwalter':
        flash('Du hast keine Berechtigung, Rezepte zu löschen.', 'danger')
        return redirect(url_for('recipes'))

    conn = get_db_connection()
    if not conn:
        flash("Fehler bei der Verbindung zur Datenbank.", 'danger')
        return redirect(url_for('recipes'))

    cursor = conn.cursor()

    try:
        # Zuerst Nährwerte löschen, um Fremdschlüssel-Probleme zu vermeiden
        cursor.execute("DELETE FROM naehrwerte WHERE rezept_id = %s", (recipe_id,))
        conn.commit()

        # Jetzt das Rezept selbst löschen
        cursor.execute("DELETE FROM rezepte WHERE id = %s", (recipe_id,))
        conn.commit()

        flash('Rezept erfolgreich gelöscht!', 'success')
    except Exception as e:
        flash(f'Fehler beim Löschen des Rezepts: {str(e)}', 'danger')
        conn.rollback()  # Falls ein Fehler auftritt, wird die Transaktion zurückgesetzt
    finally:
        conn.close()

    return redirect(url_for('recipes'))

# Route für das Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
