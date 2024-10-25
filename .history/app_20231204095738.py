from flask import Flask, render_template, request, redirect, url_for, session, flash
from neo4j import GraphDatabase

app = Flask(__name__, static_folder='static')
app.secret_key = 'qRt9pL2sF7gY3wX8zA6c'

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Vaibhav@123"

class Neo4jDB:
    def __init__(self, uri, user, password):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))

    def close(self):
        self._driver.close()

    def create_user(self, username, password):
        with self._driver.session() as session:
            session.write_transaction(self._create_user, username, password)

    def _create_user(self, tx, username, password):
        query = "CREATE (u:User {username: $username, password: $password})"
        tx.run(query, username=username, password=password)

    def get_user(self, username):
        with self._driver.session() as session:
            return session.read_transaction(self._get_user, username)

    def _get_user(self, tx, username):
        query = "MATCH (u:User {username: $username}) RETURN u"
        result = tx.run(query, username=username)
        return result.single()

    def create_itinerary(self, username, location):
        with self._driver.session() as session:
            session.write_transaction(self._create_itinerary, username, location)

    def _create_itinerary(self, tx, username, location):
        query = (
            "MATCH (u:User {username: $username})"
            "MERGE (l:Location {location: $location})"
            "MERGE (u)-[:HAS_ITINERARY]->(l)"
        )
        tx.run(query, username=username, location=location)

    def get_similar_locations(self, zipcode):
        with self._driver.session() as session:
            return session.read_transaction(self._get_similar_locations, zipcode)

    def _get_similar_locations(self, tx, zipcode):
        query = (
            "MATCH (l1:Location {zipcode: $zipcode})-[:IS_NEIGHBOR_OF]->(l2:Location)"
            "RETURN l2.location as similar_location"
        )
        result = tx.run(query, zipcode=zipcode)
        return result.data()

neo4j_db = Neo4jDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = neo4j_db.get_user(username)

    if user and user['u']['password'] == password:
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid login credentials', 'error')
        return redirect(url_for('index'))

@app.route('/signup', methods=['POST'])
def signup():
    # Use the correct field name from your form
    username = request.form['username']
    fullname = request.form['fullname']
    email = request.form['email']
    password = request.form['password']

    existing_user = neo4j_db.get_user(username)
    if existing_user:
        flash('Username already exists. Please choose a different username.', 'error')
        return redirect(url_for('index'))

    neo4j_db.create_user(username, password)
    flash('Account created successfully. You can now log in.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    
    if not username:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('index'))

    return render_template('dashboard.html')

@app.route('/new_itinerary', methods=['GET', 'POST'])
def new_itinerary():
    username = session.get('username')
    
    if not username:
        flash('Please log in to create a new itinerary.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        location = request.form['location']
        
        neo4j_db.create_itinerary(username, location)
        similar_locations = neo4j_db.get_similar_locations(location)
        
        return render_template('results.html', results=similar_locations, category='Locations')

    return render_template('new_itinerary.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)