from bs4 import BeautifulSoup
import requests
import json
import secrets
import sqlite3

base_url='https://www.rottentomatoes.com/'
endpoint_url='http://www.omdbapi.com/'
client_key = secrets.API_KEY
DB_NAME = 'bestmovies.sqlite'

CACHE_FILENAME = "cache.json"
CACHE_DICT = {}


# PART 1 Web Crawling in Rotten Tomatoes

def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

def build_genre_url_dict():
    ''' Make a dictionary that maps genre to genre page url from "https://www.rottentomatoes.com/top/bestofrt/"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a genre name and value is the url
        e.g. {'comedy':'https://www.rottentomatoes.com/top/bestofrt/top_100_comedy_movies/', ...}
    '''

    genre_url_dict={}
    url=base_url+'/top/bestofrt/'
    if url in CACHE_DICT.keys():
        print("Using Cache")
        response = CACHE_DICT[url]
        soup = BeautifulSoup(response, 'html.parser')
    else:
        print("Fetching")
        response = requests.get(url)
        CACHE_DICT[url] = response.text
        save_cache(CACHE_DICT)
        soup = BeautifulSoup(response.text, 'html.parser')
    lis=soup.find('ul',class_='dropdown-menu').find_all('li')
    for li in lis:
        genre_url=base_url+li.find('a')['href']
        genre=li.find('a').text.strip().lower()
        genre_url_dict[genre]=genre_url 
    return genre_url_dict


class Movie:
    '''a movie

    Instance Attributes
    -------------------
    rank: string
        the rank of a movie in a certain category(e.g. '1.', '2.')
    
    title: string
        the title of a movie (e.g. 'Coco')

    score: string
        the score of a movie (e.g. '97%')

    url: string
        the url of a movie (e.g. 'https://www.rottentomatoes.com/m/lady_bird')
    '''
    def __init__(self,tr):
        self.rank=int(tr.find('td', class_='bold').text.strip().strip('.'))
        self.title=tr.find('a', class_='unstyled articleLink').text.strip()
        self.score=int(tr.find('span', class_='tMeterScore').text.strip().strip('%'))
        self.url='https://www.rottentomatoes.com'+tr.find('a', class_='unstyled articleLink')['href']
    

    def info(self):
        '''Get basic information of a movie.

        Parameters
        ----------
        none

        Returns
        -------
        str
            The basic information about a movie in the format of "rank title: scores
        '''
        info=f"{self.rank} {self.title}: {self.score}"
        return info
    
    def create_bestmovies_json(self):
        bestmoviesdic={'rank':self.rank, 'title':self.title, 'score':self.score}
        bestmovies=json.dumps(bestmoviesdic)
        return bestmovies

def get_movies_for_genre(genre_url):
    '''Make a list of movie instances from a genre URL.
    
    Parameters
    ----------
    genre_url: string
        The URL for a movie genre
        
    
    Returns
    -------
    list
        a list of movie instances of the certain genre
    '''
    movies_for_genre=[]
    if genre_url in CACHE_DICT.keys():
        print("Using Cache")
        response= CACHE_DICT[genre_url]
        soup = BeautifulSoup(response, 'html.parser')
    else:
        print("Fetching")
        response = requests.get(genre_url)
        CACHE_DICT[genre_url] = response.text
        save_cache(CACHE_DICT)
        soup = BeautifulSoup(response.text, 'html.parser')
    trs=soup.find('table', class_='table').find_all('tr')
    for tr in trs[1:]:
        instance=Movie(tr)
        movies_for_genre.append(instance)      
    return movies_for_genre




# Part 2 Working with API of The Open Movie Database

def construct_unique_key(endpoint_url, params):
    ''' constructs a key that is guaranteed to uniquely and 
    repeatably identify an API request by its endpoint_url and params
    
    Parameters
    ----------
    endpoint_url: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs
    
    Returns
    -------
    string
        the unique key as a string
    '''
    param_strings = []
    connector = '_'
    for k in params.keys():
        param_strings.append(f'{k}_{params[k]}')
    param_strings.sort()
    unique_key = endpoint_url + connector + connector.join(param_strings)
    return unique_key


def make_request_with_cache(endpoint_url, client_key, name):
    '''Check the cache for a saved result for this baseurl+params:values
    combo. If the result is found, return it. Otherwise send a new 
    request, save it, then return it.
    
    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    phashtag: string
        The hashtag to search (i.e. “#2020election”)
    count: int
        The number of tweets to retrieve
    
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
    params = {'apikey': client_key, 't':name}
    unique_key=construct_unique_key(endpoint_url, params)
    if unique_key in CACHE_DICT.keys():
	    results = CACHE_DICT[unique_key]
    else:
        results = requests.get(endpoint_url, params=params).json()
        CACHE_DICT[unique_key] = results
        save_cache(CACHE_DICT)
    return results




# Part 3 Data Storage
class Film:
    '''a film

    Instance Attributes
    -------------------
    synopsis: string
        the synopsis of a movie 
    
    rating: string
        the rating a national site (e.g. 'G','R')

    genre: string
        the genres of a movie (e.g. 'Classics', 'Comedy', 'Romance')

    director: string
        the director(s) of a movie (e.g. 'Mark Sandrich')

    writer: string
        the writers a movie (e.g. 'Dwight Taylor, Allan Scott')

    time: string
        the release time of a movie (e.g. 'Sep 6, 1935')

    box: string
        the box office of a movie (e.g. '$48,285,330')

    length: string
        the length of a movie in minutes (e.g. '93 minutes')

    studio: string
        the studio that produced the movie (e.g. 'Turner Home Entertainment')

    actors: string
        the actors of a movie (e.g. 'Tom Hanks, Tim Allen, Annie Potts, Tony Hale')
    '''
    def __init__(self,movie_title, movie_url):
        if movie_url in CACHE_DICT.keys():
            print("Using Cache")
            response= CACHE_DICT[movie_url]
            soup = BeautifulSoup(response, 'html.parser')
        else:
            print("Fetching")
            response = requests.get(movie_url)
            CACHE_DICT[movie_url] = response.text
            save_cache(CACHE_DICT)
            soup = BeautifulSoup(response.text, 'html.parser')
        
        self.synopsis=soup.find('div',id='movieSynopsis').text.strip()

        lis=soup.find('ul', class_='content-meta info').find_all('li')

        self.rating=lis[0].find('div',class_='meta-value').text.strip()
        # genre_list=''
        # genres=lis[1].find('div', class_='meta-value').find_all('a')
        # for genre in genres:
        #     if genre_list=='':
        #         genre_list=genre_list+genre.text.strip()
        #     else:
        #         genre_list=genre_list+", "+genre.text.strip()
        # self.genre=genre_list

        director_list=''
        directors=lis[2].find('div', class_='meta-value').find_all('a')
        for director in directors:
            if director_list=='':
                director_list=director_list+director.text.strip()
            else:
                director_list=director_list+", "+director.text.strip()
        self.director=director_list

        writer_list=''
        writers=lis[3].find('div', class_='meta-value').find_all('a')
        for writer in writers:
            if writer_list=='':
                writer_list=writer_list+writer.text.strip()
            else:
                writer_list=writer_list+", "+writer.text.strip()
        self.writer=writer_list

        self.time=lis[4].find('div',class_='meta-value').find('time').text.strip()

        try:
            self.box=int(lis[6].find('div',class_='meta-value').text.strip().strip('$'))
            self.length=int(lis[7].find('div',class_='meta-value').find('time').text.strip('minutes'))
            self.studio=lis[8].find('div',class_='meta-value').text.strip()
        except:
            self.box=None
            try:
                self.length=int(lis[6].find('div',class_='meta-value').find('time').text.strip().strip('minutes'))
                self.studio=lis[7].find('div',class_='meta-value').text.strip()
            except:
                self.length=NotImplemented
                self.studio=lis[6].find('div',class_='meta-value').text.strip()

        
        results=make_request_with_cache(endpoint_url, client_key, movie_title[0:-7])  
        self.genre=results['Genre']
        self.actors=results['Actors']
        self.language=results['Language']
        self.country=results['Country']
        self.awards=results['Awards']
        self.metascore=results['Metascore']
        self.imdb=results['imdbRating']
        ratings=results['Ratings']
        for source in ratings:
            if source['Source']=='Rotten Tomatoes':
                self.rottentomatoes=source['Value']
        

    def info(self):
        '''Get detailed information of a film.

        Parameters
        ----------
        none

        Returns
        -------
        str
            The detailed information about a movie including a synopsis, its rating, genres, director, writers, release time, box office, runtime and studio
        '''
        info=f"Synopsis:\n{self.synopsis}\nRating:{self.rating}\nGenre: {self.genre}\nDirected By: {self.director}\nWritten By: {self.writer}\nIn Theaters: {self.time}\nBox Office: {self.box}\nRuntime: {self.length}\nStudio: {self.studio}\nActors: {self.actors}\nMetascore: {self.metascore}\nimdbRating: {self.imdb}"
        return info


def create_db():
    '''
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    drop_bestmovies_sql = 'DROP TABLE IF EXISTS "BestMovies"'
    drop_ratings_sql = 'DROP TABLE IF EXISTS "Ratings"'
    drop_movieinfo_sql = 'DROP TABLE IF EXISTS "MovieInfo"'

    create_bestmovies_sql = '''
        CREATE TABLE IF NOT EXISTS "BestMovies" (
            "Rank" INTEGER PRIMARY KEY,
            "Title" TEXT NOT NULL, 
            "Score" INTEGER
        )
    '''
    create_ratings_sql = '''
        CREATE TABLE IF NOT EXISTS 'Ratings'(
            "Rank" INTEGER PRIMARY KEY,
            'Title' TEXT NOT NULL,
            'RottenTomatoes' INTEGER,
            'Metacritic' REAL,
            'IMDB' REAL
        )
    '''
    create_movieinfo_sql = '''
        CREATE TABLE IF NOT EXISTS 'MovieInfo'(
            "Rank" INTEGER PRIMARY KEY,
            'Title' TEXT NOT NULL,
            'Rating' TEXT NOT NULL,
            'Synopsis' TEXT NOT NULL,
            'Genres' TEXT NOT NULL,
            'Director' TEXT NOT NULL,
            'Writers' TEXT NOT NULL,
            'ReleaseTime' TEXT NOT NULL,
            'BoxOffice' INTEGER,
            'Length' INTEGER,
            'Studio' TEXT NOT NULL,
            'Actors' TEXT NOT NULL,
            'Language' TEXT NOT NULL,
            'Country' TEXT NOT NULL,
            'Awards' TEXT NOT NULL
        )
    '''
    cur.execute(drop_bestmovies_sql)
    cur.execute(drop_ratings_sql)
    cur.execute(drop_movieinfo_sql)
    cur.execute(create_ratings_sql)
    cur.execute(create_bestmovies_sql)
    cur.execute(create_movieinfo_sql)
    conn.commit()
    conn.close()


def load_bestmovies(movies_for_genre): 

    insert_country_sql = '''
        INSERT INTO BestMovies
        VALUES (?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for c in movies_for_genre:
        cur.execute(insert_country_sql,
            [
                c.rank,
                c.title,
                c.score
            ]
        )
    conn.commit()
    conn.close()

def load_ratings(index, movie_title, movie_url): 
    rank=index+1
    film=Film(movie_title, movie_url)

    insert_country_sql = '''
        INSERT INTO Ratings
        VALUES (?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(insert_country_sql,
        [   
            rank,
            movie_title,
            film.rottentomatoes,
            film.metascore,
            film.imdb
        ]
    )
    conn.commit()
    conn.close()


def load_movieinfo(index, movie_title, movie_url): 
    rank=index+1
    movieinfo = Film(movie_title, movie_url)

    insert_country_sql = '''
        INSERT INTO MovieInfo
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(insert_country_sql,
        [
            rank,
            movie_title,
            movieinfo.synopsis,
            movieinfo.genre,
            movieinfo.rating,
            movieinfo.director,
            movieinfo.writer,
            movieinfo.time,
            movieinfo.box,
            movieinfo.length,
            movieinfo.studio,
            movieinfo.actors,
            movieinfo.language,
            movieinfo.country,
            movieinfo.awards
        ]
    )
    conn.commit()
    conn.close()



if __name__ == "__main__":
    genre_url_dict=build_genre_url_dict()
    create_db()
    while True:
        genre_name=input('Enter a movie genre or "exit": ')
        if genre_name=="exit":
            break
        elif genre_name.lower() in genre_url_dict.keys():
            movies_for_genre=get_movies_for_genre(genre_url_dict[genre_name.lower()])
            print("-----------------------------------")
            print(f"List of top {genre_name} movies")
            print("-----------------------------------")
            load_bestmovies(movies_for_genre)
            for movies in movies_for_genre:
                print(movies.info())
            while True:
                number=input('Choose the number for detailed information or "exit" or "back": ')
                if number=="back":
                    break
                elif number.isnumeric():
                    if 0<int(number)<=len(movies_for_genre):
                        index=int(number)-1
                        print(Film(movies_for_genre[index].title, movies_for_genre[index].url).info())
                        load_ratings(index, movies_for_genre[index].title, movies_for_genre[index].url)
                        load_movieinfo(index, movies_for_genre[index].title, movies_for_genre[index].url)
                    else:
                        print("[Error] Invalid input")
                        print("-------------------------------\n")
                elif number=="exit":
                    quit()
                else:
                    print("[Error] Invalid input")
                    print("-------------------------------\n")


