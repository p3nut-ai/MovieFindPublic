from flask import Flask, flash,render_template, request, jsonify, redirect, session, url_for
import requests
import sqlite3
import random
from bs4 import BeautifulSoup
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user


app = Flask(__name__)
app.config['SECRET_KEY'] = 'AsdsUasdask'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

OMDB_API_KEY = '8ca55281'
OMDB_API_URL = 'http://www.omdbapi.com/'


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1])  # user_id, username
    return None

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


def create_table():


    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()

    # Create the 'users' table to store usernames and passwords
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')

    # Create the 'watchlist' table for storing movie data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT,
        rating TEXT,
        plot TEXT,
        director TEXT,
        poster TEXT,
        username TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')

    # Commit the changes and close the connection
    conn.commit()

    # Insert default user (you can change this as needed)
    cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("test@email.com", "testAdmin"))
    conn.commit()

    conn.close()

    print("Database and tables created successfully!")


def get_youtube_url(query):
    search_query = query.replace(' ', '+')
    url = f"https://www.youtube.com/results?search_query={search_query}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for video in soup.find_all('a', href=True):
            if '/watch?v=' in video['href']:
                video_url = f"https://www.youtube.com{video['href']}"
                return video_url
    return None

def get_most_viewed_trailer(movie_title):
    api_key = 'AIzaSyDOAie_op5V193JH-pD5wuTnvHIvmrLDmY'  # Replace with your YouTube API Key
    base_url = 'https://www.googleapis.com/youtube/v3/search'

    # Define the search query parameters
    params = {
        'part': 'snippet',
        'q': f'{movie_title} trailer',  # Search for the movie title + trailer
        'key': api_key,
        'type': 'video',
        'maxResults': 5  # Limit the number of results
    }

    # Send the request to the YouTube API
    response = requests.get(base_url, params=params)
    print(response)
    data = response.json()

    if response.status_code == 200:
        print('Working')
    else:
        print("error")

    # Filter results for the word 'trailer' in the title and get video IDs
    video_urls = []
    for item in data.get('items', []):
        title = item['snippet']['title'].lower()
        if 'trailer' in title:
            video_id = item['id']['videoId']
            video_urls.append(f'https://www.youtube.com/watch?v={video_id}')

    # If video URLs exist, proceed to get the most viewed one
    if video_urls:
        # Get the statistics for each video to filter by view count
        video_stats_url = 'https://www.googleapis.com/youtube/v3/videos'
        video_stats_params = {
            'part': 'statistics',
            'id': ','.join([video_id.split('=')[-1] for video_id in video_urls]),
            'key': api_key
        }
        stats_response = requests.get(video_stats_url, params=video_stats_params)
        stats_data = stats_response.json()

        # Find the video with the highest view count
        max_views = 0
        most_viewed_url = ''
        for video in stats_data['items']:
            views = int(video['statistics']['viewCount'])
            if views > max_views:
                max_views = views
                most_viewed_url = f'https://www.youtube.com/embed/{video["id"]}'

        return most_viewed_url
    else:
        return "No trailer found"

def get_db_connection():
    conn = sqlite3.connect('watchlist.db')
    conn.row_factory = sqlite3.Row
    return conn

url = None


@app.route('/no_page')
def errorP():
    return render_template('404.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to SQLite database and verify credentials
        conn = sqlite3.connect('watchlist.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            session['username'] = user_data[0]
            user = User(user_data[0], user_data[1])
            login_user(user)
            return redirect(url_for('main_page'))
        else:
            flash('Login failed. Check your username and/or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/main_page_test')
def test_main_page():
    return render_template('testing.html')

@app.route('/main_page')
def main_page():
     # Fetch the watchlist from the database
    conn = sqlite3.connect('watchlist.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM watchlist')
    movies = cursor.fetchall()
    conn.close()


    # Pass the movie list to the template
    return render_template('index.html', movies=movies)
    # return render_template("index.html")


@app.route('/validate')
def validate():
    return render_template('index.html')

@app.route('/')
def index():

    return render_template('login.html')


@app.route("/watchlist", methods=["POST"])
def watchlist():
    # Check if you are not unintentionally adding a movie right after a delete
    if request.endpoint == "delete_movie":
        return redirect(url_for("index"))

    # Insert logic for adding a movie to the database
    title = request.form.get('title')

    print(f"Title Received: {title}")

    genre = request.form.get('genre')
    rating = request.form.get('rating')
    plot = request.form.get('plot')
    director = request.form.get('director')
    poster = request.form.get('poster')
    username = session.get('username')

    # Save the movie to the database
    try:
        # print("INSERT")
        conn = sqlite3.connect('watchlist.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO watchlist (title, genre, rating, plot, director, poster, username)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, genre, rating, plot, director, poster, username))


        conn.commit()
        conn.close()
        message = "Movie added to watchlist!"
    except Exception as e:
        print(e)

    # Redirect to the main page or render the watchlist
    return redirect(url_for('main_page'))




def check_url(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False



# API endpoint to search the database for a movie
@app.route("/check_database_movies", methods=["POST"])
def check_database_movies():
    # Get the search text from the AJAX request
    search_text = request.json.get("title", "").strip()

    if not search_text:
        return jsonify({"error": "No search text provided"}), 400

    # Query the database for matching movies
    conn = get_db_connection()
    query = "SELECT * FROM watchlist WHERE title LIKE ? OR genre LIKE ?"
    cursor = conn.execute(query, (f"%{search_text}%", f"%{search_text}%"))
    movies = cursor.fetchall()
    conn.close()

    # Get the most viewed trailer URL
    trailer_url = get_most_viewed_trailer(search_text)

    # Prepare search URLs
    search_title = search_text.replace(" ", "+")
    netflix_url = f"https://www.netflix.com/search?q={search_title}"
    amazon_prime_url = f"https://www.amazon.com/s?k={search_title}"
    fmovies_url = f"https://ww4.fmovies.co/search/?q={search_title}"
    onetwothreemovies_url = f"https://ww4.123moviesfree.net/search/?q={search_title}"

    # Check the URLs and collect those that return a 200 response
    valid_urls = []
    if check_url(netflix_url):
        valid_urls.append({"name": "Netflix", "url": netflix_url})
    if check_url(amazon_prime_url):
        valid_urls.append({"name": "Amazon Prime", "url": amazon_prime_url})

    # Check both FMovies and 123Movies URLs
    fmovies_available = check_url(fmovies_url)
    onetwothreemovies_available = check_url(onetwothreemovies_url)

    # Randomly choose between FMovies and 123Movies if both are available
    if fmovies_available and onetwothreemovies_available:
        external_url = random.choice([fmovies_url, onetwothreemovies_url])
        valid_urls.append({"name": "Alternative Site", "url": external_url})
    elif fmovies_available:
        valid_urls.append({"name": "FMovies", "url": fmovies_url})
    elif onetwothreemovies_available:
        valid_urls.append({"name": "123Movies", "url": onetwothreemovies_url})

    # If no movies are found, return an empty list and valid search URLs
    if not movies:
        return jsonify({"movies": [], "search_urls": valid_urls})

    # Format the movie results
    movie_list = [
        {
            "id": movie["id"],
            "title": movie["title"],
            "genre": movie["genre"],
            "rating": movie["rating"],
            "plot": movie["plot"],
            "director": movie["director"],
            "poster": movie["poster"],
            "trailer": trailer_url
        }
        for movie in movies
    ]

    # Return the list of movies and the valid search URLs
    return jsonify({"movies": movie_list, "search_urls": valid_urls})


@app.route("/delete_movie", methods=["POST"])
def delete_movie():
    # Get the movie title from the request
    title_to_delete = request.json.get("title", "").strip()
    print(f"Received title: {title_to_delete}")

    # Check if title is provided
    if not title_to_delete:
        return jsonify({"error": "No title provided"}), 400

    conn = get_db_connection()
    try:
        query_delete = 'DELETE FROM watchlist WHERE title = ?'
        cursor = conn.execute(query_delete, (title_to_delete,))
        conn.commit()

        # Check how many rows were deleted
        if cursor.rowcount == 0:
            return jsonify({"error": f"Movie '{title_to_delete}' not found in watchlist."}), 404

        print("Success: Movie deleted.")
        return jsonify({"success": True, "message": f"Movie '{title_to_delete}' deleted successfully."})

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "An error occurred while trying to delete the movie."}), 500

    finally:
        conn.close()


@app.route('/get_movies', methods=["POST"])
def get_movies():
    data = request.get_json()
    movie_title = data.get('movie')

    # Make a request to OMDb API to get movie details
    response = requests.get(OMDB_API_URL, params={
        't': movie_title,
        'apikey': OMDB_API_KEY
    })

    if response.status_code == 200:
        data = response.json()
        if data['Response'] == 'True':  # Movie found
            movie_info = {
                'Poster': data.get('Poster'),
                'Title': data.get('Title'),
                'Director': data.get('Director'),
                'Genre': data.get('Genre'),
                'Plot': data.get('Plot'),
                'imdbRating': data.get('imdbRating')
            }

            # Fetch the most viewed trailer
            trailer_url = get_most_viewed_trailer(movie_title)
            print(trailer_url)
            movie_info['Trailer'] = trailer_url
            print(movie_info)
            return jsonify(movie_info)  # Return JSON response with trailer URL
        else:
            return jsonify({'error': 'Movie not found'}), 404
    else:
        return jsonify({'error': 'Failed to fetch data from API'}), 500




if __name__ == "__main__":
    create_table()
    app.run(debug=True)
