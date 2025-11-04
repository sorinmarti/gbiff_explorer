import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from datetime import datetime
from io import StringIO
import pandas as pd
import csv

from config import Config
from models import db, Search, Occurrence
from gbif_service import GBIFService

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Ensure instance folder exists
os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """Home page with search form and recent searches"""
    recent_searches = Search.query.order_by(Search.created_at.desc()).limit(10).all()
    return render_template('index.html', recent_searches=recent_searches)


@app.route('/search', methods=['POST'])
def search():
    """Submit a new search and download GBIF data"""
    person_name = request.form.get('person_name', '').strip()

    if not person_name:
        flash('Please enter a person name', 'error')
        return redirect(url_for('index'))

    # Create new search record
    search_record = Search(person_name=person_name, status='downloading')
    db.session.add(search_record)
    db.session.commit()

    try:
        # Initialize GBIF service
        gbif_service = GBIFService()

        # Download all occurrences
        progress_info = {'current': 0, 'total': 0}

        def progress_callback(current, total):
            progress_info['current'] = current
            progress_info['total'] = total
            print(f"Downloaded {current}/{total} records")

        raw_occurrences = gbif_service.search_by_person(
            person_name,
            progress_callback=progress_callback
        )

        # Parse and save occurrences to database
        for raw_occ in raw_occurrences:
            parsed_occ = gbif_service.parse_occurrence(raw_occ)

            # Check if occurrence already exists
            existing = Occurrence.query.filter_by(gbif_id=parsed_occ['gbif_id']).first()
            if existing:
                continue

            # Create new occurrence
            occurrence = Occurrence(
                search_id=search_record.id,
                **parsed_occ
            )
            db.session.add(occurrence)

        # Update search record
        search_record.result_count = len(raw_occurrences)
        search_record.status = 'completed'
        db.session.commit()

        flash(f'Successfully downloaded {len(raw_occurrences)} occurrences for "{person_name}"', 'success')
        return redirect(url_for('results', search_id=search_record.id))

    except Exception as e:
        search_record.status = 'error'
        search_record.error_message = str(e)
        db.session.commit()

        flash(f'Error downloading data: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/results/<int:search_id>')
def results(search_id):
    """Display results with filtering options"""
    search_record = Search.query.get_or_404(search_id)

    # Get filter parameters
    recorded_by_filter = request.args.get('recorded_by', '')
    identified_by_filter = request.args.get('identified_by', '')
    country_filter = request.args.get('country', '')
    year_min = request.args.get('year_min', type=int)
    year_max = request.args.get('year_max', type=int)
    family_filter = request.args.get('family', '')
    has_coordinates = request.args.get('has_coordinates', '')

    # Build query
    query = search_record.occurrences

    # Apply filters
    if recorded_by_filter:
        query = query.filter(Occurrence.recorded_by.ilike(f'%{recorded_by_filter}%'))
    if identified_by_filter:
        query = query.filter(Occurrence.identified_by.ilike(f'%{identified_by_filter}%'))
    if country_filter:
        query = query.filter(Occurrence.country.ilike(f'%{country_filter}%'))
    if year_min:
        query = query.filter(Occurrence.year >= year_min)
    if year_max:
        query = query.filter(Occurrence.year <= year_max)
    if family_filter:
        query = query.filter(Occurrence.family.ilike(f'%{family_filter}%'))
    if has_coordinates == 'yes':
        query = query.filter(
            Occurrence.decimal_latitude.isnot(None),
            Occurrence.decimal_longitude.isnot(None)
        )
    elif has_coordinates == 'no':
        query = query.filter(
            db.or_(
                Occurrence.decimal_latitude.is_(None),
                Occurrence.decimal_longitude.is_(None)
            )
        )

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = Config.RESULTS_PER_PAGE
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    occurrences = pagination.items

    # Get unique values for filter dropdowns
    all_countries = db.session.query(Occurrence.country).filter(
        Occurrence.search_id == search_id,
        Occurrence.country.isnot(None)
    ).distinct().order_by(Occurrence.country).all()
    countries = [c[0] for c in all_countries]

    all_families = db.session.query(Occurrence.family).filter(
        Occurrence.search_id == search_id,
        Occurrence.family.isnot(None)
    ).distinct().order_by(Occurrence.family).all()
    families = [f[0] for f in all_families]

    # Get year range
    year_stats = db.session.query(
        db.func.min(Occurrence.year),
        db.func.max(Occurrence.year)
    ).filter(
        Occurrence.search_id == search_id,
        Occurrence.year.isnot(None)
    ).first()
    min_year = year_stats[0] if year_stats[0] else 1700
    max_year = year_stats[1] if year_stats[1] else datetime.now().year

    return render_template(
        'results.html',
        search=search_record,
        occurrences=occurrences,
        pagination=pagination,
        countries=countries,
        families=families,
        min_year=min_year,
        max_year=max_year,
        filters={
            'recorded_by': recorded_by_filter,
            'identified_by': identified_by_filter,
            'country': country_filter,
            'year_min': year_min or '',
            'year_max': year_max or '',
            'family': family_filter,
            'has_coordinates': has_coordinates
        }
    )


@app.route('/export/<int:search_id>')
def export(search_id):
    """Export filtered results as CSV"""
    search_record = Search.query.get_or_404(search_id)

    # Apply same filters as results page
    recorded_by_filter = request.args.get('recorded_by', '')
    identified_by_filter = request.args.get('identified_by', '')
    country_filter = request.args.get('country', '')
    year_min = request.args.get('year_min', type=int)
    year_max = request.args.get('year_max', type=int)
    family_filter = request.args.get('family', '')
    has_coordinates = request.args.get('has_coordinates', '')

    query = search_record.occurrences

    if recorded_by_filter:
        query = query.filter(Occurrence.recorded_by.ilike(f'%{recorded_by_filter}%'))
    if identified_by_filter:
        query = query.filter(Occurrence.identified_by.ilike(f'%{identified_by_filter}%'))
    if country_filter:
        query = query.filter(Occurrence.country.ilike(f'%{country_filter}%'))
    if year_min:
        query = query.filter(Occurrence.year >= year_min)
    if year_max:
        query = query.filter(Occurrence.year <= year_max)
    if family_filter:
        query = query.filter(Occurrence.family.ilike(f'%{family_filter}%'))
    if has_coordinates == 'yes':
        query = query.filter(
            Occurrence.decimal_latitude.isnot(None),
            Occurrence.decimal_longitude.isnot(None)
        )

    occurrences = query.all()

    # Convert to DataFrame
    data = [occ.to_dict() for occ in occurrences]
    df = pd.DataFrame(data)

    # Create CSV in memory
    output = StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Create response
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=gbif_export_{search_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    )


@app.route('/delete/<int:search_id>', methods=['POST'])
def delete_search(search_id):
    """Delete a search and all its occurrences"""
    search_record = Search.query.get_or_404(search_id)
    db.session.delete(search_record)
    db.session.commit()
    flash(f'Search "{search_record.person_name}" deleted successfully', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
