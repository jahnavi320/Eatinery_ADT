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
            session.execute_write(self._create_user, username, password)

    def _create_user(self, tx, username, password):
        query = "CREATE (u:User {username: $username, password: $password})"
        tx.run(query, username=username, password=password)

    def get_user(self, username):
        with self._driver.session() as session:
            return session.execute_read(self._get_user, username)

    def _get_user(self, tx, username):
        query = "MATCH (u:User {username: $username}) RETURN u"
        result = tx.run(query, username=username)
        return result.single()

    def create_itinerary(self, username, location):
        with self._driver.session() as session:
            session.execute_write(self._create_itinerary, username, location)

    def _create_itinerary(self, tx, username, location):
        query = (
            "MATCH (u:User {username: $username})"
            "MERGE (l:Location {location: $location})"
            "MERGE (u)-[:HAS_ITINERARY]->(l)"
        )
        tx.run(query, username=username, location=location)

    def get_similar_locations(self, zipcode):
        with self._driver.session() as session:
            return session.execute_read(self._get_similar_locations, zipcode)

    def _get_similar_locations(self, tx, zipcode):
        query = (
            "MATCH (l1:Location {zipcode: $zipcode})-[:IS_NEIGHBOR_OF]->(l2:Location)"
            "RETURN l2.location as similar_location"
        )
        result = tx.run(query, zipcode=zipcode)
        return result.data()
    
    def get_user_past_itineraries(self, username):
        with self._driver.session() as session:
            return session.execute_read(self._get_user_past_itineraries, username)

    def _get_user_past_itineraries(self, tx, username):
        query = (
            "MATCH (u:User {username: $username})"
            "MATCH (u)-[:HAS_ITINERARY]->(l:Location)"
            "RETURN l.location as location, ID(l) as location_id"
        )
        result = tx.run(query, username=username)
        return result.data()
    
    def get_similar_restaurants(self, location_name, cuisine):
        with self._driver.session() as session:
            return session.execute_read(self._get_similar_restaurants, location_name, cuisine)

    def _get_similar_restaurants(self, tx, location_name, cuisine):
        query = (
            "MATCH (l:Location {location_name: $location_name})"
            "-[:HAS_CUISINE]->(c:Cuisine {cuisine: $cuisine})"
            "<-[:HAS_CUISINE]-(similar:Restaurant)"
            "RETURN DISTINCT similar.location_name as location_name"
        )
        result = tx.run(query, location_name=location_name, cuisine=cuisine)
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
        return 'Invalid login credentials'

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['fullname']
    password = request.form['password']
    neo4j_db.create_user(username, password)
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('index'))
# @app.route('/dashboard')
# def dashboard():
#     name = session.get('fullname')
#     print(name)
#     if 'username' in session:
#         user = neo4j_db.get_user(name)
#         return render_template('dashboard.html', user=user)  # Pass the 'user' variable to the template
#     else:
#         flash('Please log in to access the dashboard.', 'error')
#         return redirect(url_for('index'))


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
@app.route('/past_itineraries')
def past_itineraries():
    username = session.get('username')

    if not username:
        flash('Please log in to access past itineraries.', 'error')
        return redirect(url_for('index'))

    past_itineraries = neo4j_db.get_user_past_itineraries(username)
    return render_template('past_itineraries.html', past_itineraries=past_itineraries)

@app.route('/restaurants', methods=['GET', 'POST'])
def restaurants():
    username = session.get('username')
    selected_option = None

    
    if not username:
        flash('Please log in to access restaurant recommendations.', 'error')
        return redirect(url_for('index'))

    # if request.method == 'POST':
    #     location_name = request.form['location_name']
    #     cuisine = request.form['cuisine']

    if request.method == 'POST':
        location_name = request.form['location_name']
        cuisine = request.form['cuisine']
        selected_option = request.form['search_option']
        selected_CR = request.form['selected_CR']
        print(selected_option , selected_CR)
        # Call the Neo4j function to get similar restaurants
        similar_restaurants = neo4j_db.get_similar_restaurants(location_name, cuisine)

        return render_template('restaurants.html', similar_restaurants=similar_restaurants)

    return render_template('restaurants.html', similar_restaurants=[])




if __name__ == '__main__':
    app.run(debug=True, port=5001)