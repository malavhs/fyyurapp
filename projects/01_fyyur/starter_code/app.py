#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from audioop import add
from email.policy import default
from enum import unique
import json
from os import abort
from tracemalloc import start
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
import logging
from flask_migrate import Migrate
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import ForeignKey
from forms import *
import sys
import datetime
import os
from models import db, Show, Venue, Artist

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#
app = Flask(__name__)
moment = Moment(app)
db.app = app
db.init_app(app)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
migrate = Migrate(app, db) # Define migrate to use the flask app as well as the db

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # replace with real venues data.
  # num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
  data = db.session.query(Show).join(Venue).join(Artist).all()

  shows = []
  for a in data:
    shows.append({
      'venue_id': a.venue_id,
      'venue_name': a.venue.name,
      'artist_id' : a.artist_id,
     'artist_name' : a.artist.name,
     'artist_image_link' : a.artist.image_link,
     'start_time' : a.start_time.strftime('%Y-%m-%d %H:%M:%S') 
    })
  data = []
  for dist_area in db.session.query(Venue).distinct(Venue.city, Venue.state):
    venue_data = []
    for dist_venue in Venue.query.filter(Venue.city == dist_area.city).filter(Venue.state == dist_area.state).all():
      venue_data.append({
        "id": dist_venue.id,
        "name": dist_venue.name,
        "num_upcoming_shows":  db.session.query(Show).join(Venue).join(Artist).filter(Venue.id == dist_venue.id).filter(Show.start_time > datetime.datetime.utcnow()).count()
      })
    data.append({
      "city" : dist_area.city,
      "state": dist_area.state,
      "venues": venue_data
    })

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # implement search on venues with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  search_term = request.form.get('search_term', '') 
  search_query = Venue.query.filter(Venue.name.ilike(f'%{search_term}%'))
  counts = search_query.count()

  data = []
  for search_data in search_query:
    upcoming_shows = db.session.query(Show).join(Venue).join(Artist).filter(Venue.id == search_data.id).filter(Show.start_time > datetime.datetime.utcnow()).count()
    data.append({
      "id": search_data.id,
      "name": search_data.name,
      "num_upcoming_shows": upcoming_shows
    })
    
  response={
    "count": counts,
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # replace with real venue data from the venues table, using venue_id

  venue_data = Venue.query.filter_by(id = venue_id).all()[0]
  past_shows = db.session.query(Show).join(Venue).join(Artist).filter(Venue.id == venue_id).filter(Show.start_time < datetime.datetime.utcnow())
  upcoming_shows = db.session.query(Show).join(Venue).join(Artist).filter(Venue.id == venue_id).filter(Show.start_time > datetime.datetime.utcnow()) 
  past_shows_arr = []
  upp_shows_arr = []
  for a in past_shows:
    past_shows_arr.append({
      "artist_id": a.artist.id,
      "artist_name": a.artist.name,
      "artist_image_link": a.artist.image_link,
      "start_time": a.start_time.strftime('%Y-%m-%d %H:%M:%S') 

    })

  for b in upcoming_shows:
    upp_shows_arr.append({
      "artist_id": b.artist.id,
      "artist_name": b.artist.name,
      "artist_image_link": b.artist.image_link,
      "start_time": b.start_time.strftime('%Y-%m-%d %H:%M:%S') 

    })
  data = {
      'id': venue_data.id,
      'name': venue_data.name,
      'genres': venue_data.genres,
      'address': venue_data.address,
      'city': venue_data.city,
      'state': venue_data.state,
      'phone': venue_data.phone,
      'image_link': venue_data.image_link,
      'website': venue_data.website_link,
      'facebook_link': venue_data.facebook_link,
      'seeking_talent': venue_data.seeking_talent,
      'seeking_description': venue_data.seeking_description,
      'past_shows': past_shows_arr,
      'upcoming_shows': upp_shows_arr,
      'past_shows_count':past_shows.count(),
      'upcoming_shows_count': upcoming_shows.count()

  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # insert form data as a new Venue record in the db, instead
  #  modify data to be the data object returned from db insertion

  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    image_link = request.form['image_link']  
    genres =  request.form.getlist('genres')
    facebook_link = request.form['facebook_link']
    website_link = request.form['website_link']
    seeking_talent = request.form['seeking_talent']
    if seeking_talent == 'y':
      seeking_talent = True
    elif seeking_talent == 'n':
      seeking_talent = False
    seeking_description = request.form['seeking_description']
    
    venue = Venue(name=name, city = city, state = state, address = address, phone = phone, genres = genres, image_link = image_link, facebook_link = facebook_link, website_link = website_link, seeking_talent = seeking_talent, seeking_description = seeking_description)
    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()  
  if error:
    flash('ERROR: Venue ' + request.form['name'] + ' was NOT successfully listed!')
    return render_template('pages/home.html')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')

# on successful db insert, flash success
  
  # on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
      venue = Venue.query.get(venue_id)
      db.session.delete(venue)
      db.session.commit()
  except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
  finally:
      db.session.close()
      if error:
          flash('An error occurred: Venue ' + request.form['name'] + ' could not be deleted')
      else:
          flash('Venue ' + request.form['name'] + ' was successfully deleted!')

  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  #replace with real data returned from querying the database
  data = Artist.query.all()
  # data=[{
  #   "id": 4,
  #   "name": "Guns N Petals",
  # }, {
  #   "id": 5,
  #   "name": "Matt Quevedo",
  # }, {
  #   "id": 6,
  #   "name": "The Wild Sax Band",
  # }]
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term = request.form.get('search_term', '') 
  search_query = Artist.query.filter(Artist.name.ilike(f'%{search_term}%'))
  counts = search_query.count()

  data = []
  for search_data in search_query:
    upcoming_shows = db.session.query(Show).join(Venue).join(Artist).filter(Venue.id == search_data.id).filter(Show.start_time > datetime.datetime.utcnow()).count()
    data.append({
      "id": search_data.id,
      "name": search_data.name,
      "num_upcoming_shows": upcoming_shows
    })
    
  response={
    "count": counts,
    "data": data
  }
  
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  # replace with real artist data from the artist table, using artist_id
  artist_data = Artist.query.filter_by(id = artist_id).all()[0]
  #data = Artist.query.get(artist_id)
  past_shows = db.session.query(Show).join(Venue).join(Artist).filter(Artist.id == artist_id).filter(Show.start_time < datetime.datetime.utcnow())
  upcoming_shows = db.session.query(Show).join(Venue).join(Artist).filter(Artist.id == artist_id).filter(Show.start_time > datetime.datetime.utcnow()) 
  past_shows_arr = []
  upp_shows_arr = []
  for old_shows in past_shows:
    past_shows_arr.append({
      "venue_id": old_shows.venue.id,
      "venue_name": old_shows.venue.name,
      "venue_image_link": old_shows.venue.image_link,
      "start_time": old_shows.start_time.strftime('%Y-%m-%d %H:%M:%S') 

    })

  for new_shows in upcoming_shows:
    upp_shows_arr.append({
      "venue_id": new_shows.venue.id,
      "venue_name": new_shows.venue.name,
      "venue_image_link": new_shows.venue.image_link,
      "start_time": new_shows.start_time.strftime('%Y-%m-%d %H:%M:%S') 

    })
  data = {
      'id': artist_data.id,
      'name': artist_data.name,
      'genres': artist_data.genres,
      'city': artist_data.city,
      'state': artist_data.state,
      'phone': artist_data.phone,
      'image_link': artist_data.image_link,
      'website': artist_data.website_link,
      'facebook_link': artist_data.facebook_link,
      'seeking_venue': artist_data.seeking_venue,
      'seeking_description': artist_data.seeking_description,
      'past_shows': past_shows_arr,
      'upcoming_shows': upp_shows_arr,
      'past_shows_count':past_shows.count(),
      'upcoming_shows_count': upcoming_shows.count()

  }
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist_info = Artist.query.get(artist_id)
  form.name.data = artist_info.name
  form.city.data = artist_info.city
  form.state.data = artist_info.state
  form.phone.data = artist_info.phone
  form.genres.data = artist_info.genres
  form.facebook_link.data = artist_info.facebook_link
  form.image_link.data = artist_info.image_link
  form.website_link.data = artist_info.website_link
  form.seeking_venue.data = artist_info.seeking_venue
  form.seeking_description.data = artist_info.seeking_description

  #populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist_info)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    artist = Artist.query.get(artist_id)
    artist.name = request.form['name']
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.image_link = request.form['image_link']  
    artist.genres =  request.form.getlist('genres')
    artist.facebook_link = request.form['facebook_link']
    artist.website_link = request.form['website_link']
    seeking_venue = request.form['seeking_venue']
    if seeking_venue == 'y':
      seeking_venue = True
    elif seeking_venue == 'n':
      seeking_venue = False
    artist.seeking_venue  = seeking_venue
    artist.seeking_description = request.form['seeking_description']
    db.session.commit()    
  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()  

  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue_info = Venue.query.get(venue_id)
  form.name.data = venue_info.name
  form.city.data = venue_info.city
  form.address.data = venue_info.address
  form.state.data = venue_info.state
  form.phone.data = venue_info.phone
  form.genres.data = venue_info.genres
  form.facebook_link.data = venue_info.facebook_link
  form.image_link.data = venue_info.image_link
  form.website_link.data = venue_info.website_link
  form.seeking_talent.data = venue_info.seeking_talent
  form.seeking_description.data = venue_info.seeking_description 
  venue={
    "id":venue_info.id ,
    "name": venue_info.name,
    "genres": venue_info.genres,
    "address": venue_info.address,
    "city": venue_info.city,
    "state": venue_info.state,
    "phone": venue_info.phone,
    "website": venue_info.website_link,
    "facebook_link": venue_info.facebook_link,
    "seeking_talent": venue_info.seeking_talent,
    "seeking_description": venue_info.seeking_description,
    "image_link": venue_info.image_link
  }
  # populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    venue.name = request.form['name']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.address = request.form['address']
    venue.image_link = request.form['image_link']  
    venue.genres =  request.form.getlist('genres')
    venue.facebook_link = request.form['facebook_link']
    venue.website_link = request.form['website_link']
    seeking_talent = request.form['seeking_talent']
    if seeking_talent == 'y':
      seeking_talent = True
    elif seeking_talent == 'n':
      seeking_talent = False
    venue.seeking_talent  = seeking_talent
    venue.seeking_description = request.form['seeking_description']
    db.session.commit()    
  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()   
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  form.validate()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # insert form data as a new Venue record in the db, instead
  # modify data to be the data object returned from db insertion

  
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    image_link = request.form['image_link']  
    genres =  request.form.getlist('genres')
    facebook_link = request.form['facebook_link']
    website_link = request.form['website_link']
    seeking_venue = request.form['seeking_venue']
    if seeking_venue == 'y':
      seeking_venue = True
    elif seeking_venue == 'n':
      seeking_venue = False
    seeking_description = request.form['seeking_description']
    
    artist = Artist(name=name, city = city, state = state, phone = phone, genres = genres, image_link = image_link, facebook_link = facebook_link, website_link = website_link, seeking_venue = seeking_venue, seeking_description = seeking_description)
    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()  
  if error:
    flash('ERROR OCCURRED: Artist ' + request.form['name'] + ' was NOT successfully listed!')
    return render_template('pages/home.html')
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')
  # on successful db insert, flash success
  # on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # replace with real venues data.
  data = db.session.query(Show).join(Venue).join(Artist).all()
  shows = []
  for details in data:
    shows.append({
      'venue_id': details.venue_id,
      'venue_name': details.venue.name,
      'artist_id' : details.artist_id,
     'artist_name' : details.artist.name,
     'artist_image_link' : details.artist.image_link,
     'start_time' : details.start_time.strftime('%Y-%m-%d %H:%M:%S') 
    })

  return render_template('pages/shows.html', shows=shows)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # insert form data as a new Show record in the db, instead
  
  error = False
  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']
    
    show = Show(artist_id=artist_id, venue_id = venue_id, start_time = start_time)
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()  
  if error:
    flash('Show was NOT successfully listed!')
    return render_template('pages/home.html')
  else:
    flash('Show was successfully listed!')
    return render_template('pages/home.html')

  # on successful db insert, flash success
  flash('Show' +start_time+ 'was successfully listed!')
  # on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.debug = True
#     app.run()

# Or specify port manually:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)

