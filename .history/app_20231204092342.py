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

    def create_recommendation(self, username, location):
        with self._driver.session() as session:
            session.write_transaction(self._create_recommendation, username, location)

    def _create_recommendation(self, tx, username, location):
        query = (
            "MATCH (u:User {username: $username})"
            "MERGE (l:Location {location: $location})"
            "MERGE (u)-[:RECOMMENDS]->(l)"
        )
        tx.run(query, username=username, location=location)

    def get_similar_restaurants(self, cuisine):
        with self._driver.session() as session:
            return session.read_transaction(self._get_similar_restaurants, cuisine)

    def _get_similar_restaurants(self, tx, cuisine):
        query = (
            "MATCH (r:Restaurant)-[:HAS_CUISINE]->(c:Cuisine {cuisine: $cuisine})"
            "RETURN r.restaurant_name as restaurant_name"
        )
        result = tx.run(query, cuisine=cuisine)
        return result.data()

    def get_places_around_location(self, location):
        with self._driver.session() as session:
            return session.read_transaction(self._get_places_around_location, location)

    def _get_places_around_location(self, tx, location):
        query = (
            "MATCH (l1:Location {location: $location})-[:NEAR]->(l2:Location)"
            "RETURN l2.location as nearby_location"
        )
        result = tx.run(query, location=location)
        return result.data()

    def get_user_past_itineraries(self, username):
        with self._driver.session() as session:
            return session.read_transaction(self._get_user_past_itineraries, username)

    def _get_user_past_itineraries(self, tx, username):
        query = (
            "MATCH (u:User {username: $username})-[:RECOMMENDS]->(l:Location)"
            "RETURN l.location as location, ID(l) as location_id"
        )
        result = tx.run(query, username=username)
        return result.data()

# Initialize Neo4jDB
neo4j_db = Neo4jDB(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']

    existing_user = neo4j_db.get_user(username)
    if existing_user:
        flash('Username already exists. Please choose a different username.', 'error')
        return redirect(url_for('index'))

    neo4j_db.create_user(username, password)
    flash('Account created successfully. You can now log in.', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = neo4j_db.get_user(username)

    if user and user['u']['password'] == password:
        session['username'] = username
        flash('Login successful.', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid login credentials', 'error')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    username = session.get('username')

    if not username:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('index'))

    recommendations = neo4j_db.get_user_recommendations(username)
    past_itineraries = neo4j_db.get_user_past_itineraries(username)
    return render_template('dashboard.html', username=username, recommendations=recommendations, past_itineraries=past_itineraries)

@app.route('/restaurants', methods=['GET', 'POST'])
def restaurants():
    if request.method == 'POST':
        username = session.get('username')
        restaurant_name = request.form['restaurant_name']
        cuisine = request.form['cuisine']

        neo4j_db.create_recommendation(username, restaurant_name)
        similar_restaurants = neo4j_db.get_similar_restaurants(cuisine)

        return render_template('restaurants.html', similar_restaurants=similar_restaurants)
    
    return render_template('restaurants.html')

@app.route('/new_itinerary', methods=['GET', 'POST'])
def new_itinerary():
    if request.method == 'POST':
        username = session.get('username')
        location = request.form['location']

        neo4j_db.create_recommendation(username, location)
        places_around_location = neo4j_db.get_places_around_location(location)

        return render_template('new_itinerary.html', places_around_location=places_around_location)
    
    return render_template('new_itinerary.html')

@app.route('/past_itineraries')
def past_itineraries():
    username = session.get('username')

    if not username:
        flash('Please log in to access past itineraries.', 'error')
        return redirect(url_for('index'))

    past_itineraries = neo4j_db.get_user_past_itineraries(username)
    return render_template('past_itineraries.html', past_itineraries=past_itineraries)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
