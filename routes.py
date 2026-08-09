from flask import render_template, request, redirect, url_for, flash, session, jsonify, Blueprint, current_app
from extensions import db
from models import Admin, Candidate, Voter, Vote, Election
from face_recognition_utils import FaceRecognitionSystem
from werkzeug.security import check_password_hash
import cv2
import numpy as np
import base64
from datetime import datetime, date, timedelta
import random
import string
import logging
import os
import pytz
from werkzeug.utils import secure_filename
import json
# import smtplib # Removed for EmailJS
# from email.message import EmailMessage # Removed for EmailJS
from models import BlockchainRecord, OTP

bp = Blueprint('main', __name__)

# Initialize face recognition system
face_system = FaceRecognitionSystem()

def generate_voter_id():
    """Generate unique voter ID"""
    while True:
        voter_id = 'VTR' + ''.join(random.choices(string.digits, k=7))
        if not Voter.query.filter_by(voter_id=voter_id).first():
            return voter_id

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

# Removed send_email_otp function as EmailJS will handle sending from frontend
# def send_email_otp(voter, otp_code):
#     """Send OTP to voter's email"""
#     try:
#         msg = EmailMessage()
#         msg['Subject'] = 'Your VoteSense OTP for Login'
#         msg['From'] = current_app.config['MAIL_USERNAME']
#         msg['To'] = voter.email
#         msg.set_content(f'Your One-Time Password (OTP) for VoteSense login is: {otp_code}\n\nThis OTP is valid for 5 minutes. Do not share it with anyone.\n')

#         with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as smtp:
#             smtp.starttls()
#             smtp.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
#             smtp.send_message(msg)
#         logging.info(f"OTP sent to {voter.email}")
#         return True
#     except Exception as e:
#         logging.error(f"Failed to send OTP to {voter.email}: {e}")
#         return False

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        
        if role == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')
            
            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.check_password(password):
                session['admin_id'] = admin.id
                session['role'] = 'admin'
                flash('Admin login successful!', 'success')
                return redirect(url_for('main.admin_dashboard'))
            else:
                flash('Invalid admin credentials!', 'error')
                
        elif role == 'voter':
            voter_id = request.form.get('voter_id')
            
            if voter_id:
                voter = Voter.query.filter_by(voter_id=voter_id).first()
                if voter:
                    # Generate and store OTP
                    otp_code = generate_otp()
                    expires_at = datetime.utcnow() + timedelta(minutes=5) # OTP valid for 5 minutes
                    
                    # Delete any existing OTPs for this voter
                    OTP.query.filter_by(voter_id=voter.id).delete()
                    db.session.commit()

                    new_otp = OTP(voter_id=voter.id, otp_code=otp_code, expires_at=expires_at)
                    db.session.add(new_otp)
                    db.session.commit()

                    # Send OTP via email
                    if True: # EmailJS will handle sending from frontend
                        session['voter_id_for_otp'] = voter.id # Temporarily store voter_id for OTP verification
                        flash(f'OTP sent to your email ({voter.email})! Please verify.', 'info')
                        return redirect(url_for('main.verify_otp', 
                                               voter_id=voter.id, 
                                               otp_code=otp_code, 
                                               email=voter.email,
                                               service_id="service_dkbo97n", 
                                               template_id="template_xe4ax74", 
                                               public_key="7JrnJLTuEsHJuJqov"))
                    else:
                        flash('Failed to send OTP. Please try again or contact support.', 'error')
                else:
                    flash('Invalid Voter ID!', 'error')
            else:
                flash('Please enter Voter ID!', 'error')
    
    return render_template('login.html')

@bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'voter_id_for_otp' not in session:
        flash('Please enter your Voter ID to receive an OTP.', 'error')
        return redirect(url_for('main.login'))

    voter = Voter.query.get(session['voter_id_for_otp'])
    if not voter:
        flash('Voter not found. Please try again.', 'error')
        session.pop('voter_id_for_otp', None)
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        otp_entered = request.form.get('otp_code')
        if not otp_entered:
            flash('Please enter the OTP.', 'error')
            return render_template('verify_otp.html')

        # Check if OTP is valid
        stored_otp = OTP.query.filter_by(voter_id=voter.id, otp_code=otp_entered).first()

        if stored_otp and stored_otp.is_valid():
            # OTP is valid, log in the voter
            session['voter_id'] = voter.id
            session['role'] = 'voter'
            session.pop('voter_id_for_otp', None) # Clear temporary session variable
            
            # Delete the used OTP
            db.session.delete(stored_otp)
            db.session.commit()

            flash('OTP verified successfully! Welcome.', 'success')
            return redirect(url_for('main.voter_panel'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'error')
            return render_template('verify_otp.html')

    return render_template('verify_otp.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.index'))

@bp.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email') # Added email field
            address = request.form.get('address')
            gender = request.form.get('gender')
            birthdate_str = request.form.get('birthdate')
            
            # Get multiple face data inputs
            face_data_front = request.form.get('face_data_1')
            face_data_left = request.form.get('face_data_2')
            face_data_right = request.form.get('face_data_3')
            face_data_up_down = request.form.get('face_data_4')
            
            all_face_data = [face_data_front, face_data_left, face_data_right, face_data_up_down]

            # Validate required fields
            if not all([name, phone, email, address, gender, birthdate_str]) or not all(all_face_data):
                flash('All personal fields and 4 face captures are required!', 'error')
                return render_template('admin_register.html')
            
            # Parse birthdate
            birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
            
            # Generate unique voter ID
            voter_id = generate_voter_id()

            # Process multiple face data inputs
            all_extracted_encodings = [] # Collect all encodings here

            for idx, face_dat_item in enumerate(all_face_data):
                try:
                    image_data = face_dat_item.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        logging.error(f"Decoded image is None during registration for photo {idx+1}.")
                        flash(f'Error processing image data for photo {idx+1}. Please try again.', 'error')
                        return render_template('admin_register.html')
                    
                    logging.debug(f"Image shape after decoding in admin_register for photo {idx+1}: {image.shape}")
                    
                    face_encoding, _ = face_system.extract_face_encoding(image) # Extract encoding, ignore bbox
                    if face_encoding is None:
                        flash(f'No face detected in photo {idx+1}. Please try again.', 'error')
                        return render_template('admin_register.html')
                    
                    all_extracted_encodings.append(face_encoding)
                    
                except Exception as e:
                    logging.error(f"Face processing error for photo {idx+1}: {str(e)}")
                    flash(f'Error processing face data for photo {idx+1}. Please try again.', 'error')
                    return render_template('admin_register.html')
            
            # Save all collected face encodings to a single file
            if not all_extracted_encodings:
                flash('No valid face encodings were extracted from the photos. Please try again.', 'error')
                return render_template('admin_register.html')

            encoding_file_path = face_system.save_face_encoding(all_extracted_encodings, voter_id)
            if not encoding_file_path:
                flash('Error saving all face data. Please try again.', 'error')
                return render_template('admin_register.html')

            # Create new voter with a single path to the combined encoding file
            new_voter = Voter(
                voter_id=voter_id,
                name=name,
                phone=phone,
                email=email, # Added email
                address=address,
                gender=gender,
                birthdate=birthdate,
                face_encoding_path=encoding_file_path # Store a single path now
            )
            
            db.session.add(new_voter)
            db.session.commit()
            
            flash(f'Voter registered successfully! Voter ID: {voter_id}', 'success')
            return redirect(url_for('main.admin_dashboard'))
            
        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            flash(f'Registration failed. Please try again. Error: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('admin_register.html')

@bp.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))
    
    candidates = Candidate.query.all()
    voters = Voter.query.all()
    total_votes = Vote.query.count()
    
    return render_template('admin_dashboard.html', 
                         candidates=candidates, 
                         voters=voters, 
                         total_votes=total_votes)

@bp.route('/admin/add_candidate', methods=['POST'])
def add_candidate():
    if 'admin_id' not in session:
        return redirect(url_for('main.login'))
    
    try:
        name = request.form.get('name')
        symbol = request.form.get('symbol')
        state = request.form.get('state')
        district = request.form.get('district')
        taluk = request.form.get('taluk')
        
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                photo_url = '/' + file_path.replace('\\', '/') # Store as relative URL

        new_candidate = Candidate(
            name=name,
            symbol=symbol,
            state=state,
            district=district,
            taluk=taluk,
            photo_url=photo_url
        )
        
        db.session.add(new_candidate)
        db.session.commit()
        
        flash('Candidate added successfully!', 'success')
    except Exception as e:
        logging.error(f"Add candidate error: {str(e)}")
        flash('Error adding candidate!', 'error')
        db.session.rollback()
    
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/admin/voters')
def admin_voters():
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))
    voters = Voter.query.all()
    return render_template('admin_voters.html', voters=voters)

@bp.route('/admin/create_election', methods=['POST'])
def create_election():
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))
    
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        if not all([title, start_time_str, end_time_str]):
            flash('Title, start time, and end time are required for an election!', 'error')
            return redirect(url_for('main.admin_dashboard'))
        
        # Define IST timezone
        ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Parse the naive datetime from form (it's in local system time by default from datetime-local input)
        start_naive = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        end_naive = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        
        # Localize to IST, then convert to UTC and make naive for database storage
        start_time_ist_aware = ist_timezone.localize(start_naive)
        end_time_ist_aware = ist_timezone.localize(end_naive)
        
        # Convert to UTC naive for storage in the database
        start_time_utc_naive = start_time_ist_aware.astimezone(pytz.utc).replace(tzinfo=None)
        end_time_utc_naive = end_time_ist_aware.astimezone(pytz.utc).replace(tzinfo=None)
        
        if start_time_ist_aware >= end_time_ist_aware:
            flash('End time must be after start time!', 'error')
            return redirect(url_for('main.admin_dashboard'))
            
        new_election = Election(
            title=title,
            description=description,
            start_time=start_time_utc_naive,
            end_time=end_time_utc_naive,
            timezone='Asia/Kolkata', # Store timezone explicitly
            created_by=session['admin_id']
        )
        
        db.session.add(new_election)
        db.session.commit()
        
        flash('Election created successfully!', 'success')
    except Exception as e:
        logging.error(f"Error creating election: {str(e)}")
        flash(f'Error creating election: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/admin/voters/edit/<int:voter_id>', methods=['GET', 'POST'])
def admin_edit_voter(voter_id):
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))

    voter = Voter.query.get_or_404(voter_id)

    if request.method == 'POST':
        voter.name = request.form['name']
        voter.phone = request.form['phone']
        voter.email = request.form['email'] # Added email field
        voter.gender = request.form['gender']
        voter.birthdate = datetime.strptime(request.form['birthdate'], '%Y-%m-%d').date()
        voter.region = request.form['region']
        # Note: Face encoding and Voter ID are not editable via this form for security/integrity reasons
        try:
            db.session.commit()
            flash('Voter updated successfully!', 'success')
            return redirect(url_for('main.admin_voters'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating voter: {str(e)}', 'error')
            logging.error(f"Error updating voter {voter_id}: {str(e)}")
            return redirect(url_for('main.admin_voters'))
    
    return render_template('admin_edit_voter.html', voter=voter)

@bp.route('/admin/voters/delete/<int:voter_id>', methods=['POST'])
def admin_delete_voter(voter_id):
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))

    voter = Voter.query.get_or_404(voter_id)
    try:
        db.session.delete(voter)
        db.session.commit()
        flash('Voter deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting voter: {str(e)}', 'error')
        logging.error(f"Error deleting voter {voter_id}: {str(e)}")
    return redirect(url_for('main.admin_voters'))

@bp.route('/admin/candidates')
def admin_candidates():
    if 'admin_id' not in session:
        flash('Please login as admin first!', 'error')
        return redirect(url_for('main.login'))
    candidates = Candidate.query.all()
    return render_template('admin_candidates.html', candidates=candidates)

@bp.route('/voter/panel')
def voter_panel():
    if 'voter_id' not in session:
        flash('Please login as voter first!', 'error')
        return redirect(url_for('main.login'))
    
    voter = Voter.query.get(session['voter_id'])
    if not voter: # Should not happen if login is successful
        flash('Voter not found.', 'danger')
        return redirect(url_for('main.login'))
    
    candidates = Candidate.query.all()

    election = Election.query.order_by(Election.created_at.desc()).first() # Get the most recent election
    
    election_status_message = "No election has been scheduled."
    is_election_active = False
    time_until_election_start = None
    election_start_time_timestamp = None
    election_end_time_aware = None  # Initialize election_end_time_aware here
    election_end_time_for_display = None # Initialize to None
    
    if election:
        tz = pytz.timezone(election.timezone)
        now_aware = datetime.now(tz) # Current time in election's timezone
        
        # Convert stored naive UTC datetimes to aware UTC, then to election's timezone (IST)
        election_start_time_aware = pytz.utc.localize(election.start_time).astimezone(tz)
        election_end_time_aware = pytz.utc.localize(election.end_time).astimezone(tz)
        
        current_app.logger.debug(f"Voter Panel: Fetching election: {election.title} (ID: {election.id}), Start: {election_start_time_aware}, End: {election_end_time_aware}, Timezone: {election.timezone}, Current Time: {now_aware}")
        
        if now_aware < election_start_time_aware:
            # Election is scheduled for the future
            election_status_message = f"Voting will begin soon. Please wait for the election to start."
            time_until_election_start = election_start_time_aware - now_aware
            election_start_time_timestamp = election_start_time_aware.timestamp() * 1000
            is_election_active = False # Explicitly set to False
        elif election_start_time_aware <= now_aware <= election_end_time_aware:
            # Election is active
            election_status_message = "Voting is currently ACTIVE!"
            is_election_active = True
        else:
            # Election has ended
            election_status_message = "Voting has ended for this election."
            is_election_active = False

        # Assign election_end_time_for_display here inside the if block, as it's directly used below.
        # This ensures it always has a value when passed to render_template if an election exists.
        election_end_time_for_display = election_end_time_aware

    return render_template('voter_panel.html',
                           voter=voter,
                           candidates=candidates,
                           date=date,
                           election=election,
                           is_election_active=is_election_active,
                           time_until_election_start=time_until_election_start,
                           election_start_time_timestamp=election_start_time_timestamp,
                           election_status_message=election_status_message,
                           election_end_time_for_display=election_end_time_for_display) # Use the initialized variable

@bp.route('/verify_face', methods=['POST'])
def verify_face():
    if 'voter_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        voter = Voter.query.get(session['voter_id'])
        if not voter:
            return jsonify({'success': False, 'message': 'Voter not found'})
        
        if voter.has_voted:
            return jsonify({'success': False, 'message': 'You have already voted'})
        
        face_data = request.json.get('face_data')
        if not face_data:
            return jsonify({'success': False, 'message': 'No face data provided'})
        
        # Process face data
        image_data = face_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            logging.error("Decoded image is None during face verification.")
            return jsonify({'success': False, 'message': 'Error processing image data.'})
        logging.debug(f"Image shape after decoding in verify_face: {image.shape}")
        # Extract face encoding
        current_encoding, bbox = face_system.extract_face_encoding(image)
        if current_encoding is None or bbox is None:
            return jsonify({'success': False, 'message': 'No face detected in the image. Please try again.'})
        
        # Load stored encoding
        # Load the single file containing all stored encodings (which is a list)
        stored_encodings_list = face_system.load_face_encoding(voter.face_encoding_path)
        
        if stored_encodings_list is None:
            return jsonify({'success': False, 'message': 'Stored face data not found or corrupt for this voter. Please contact admin.'})
        
        # Ensure it's a list, even if only one encoding was saved
        if not isinstance(stored_encodings_list, list):
            stored_encodings_list = [stored_encodings_list]

        if not stored_encodings_list:
            return jsonify({'success': False, 'message': 'No valid stored face encodings found for this voter. Please contact admin.'})
        
        # Compare faces against all stored encodings
        match_found = False
        for stored_enc in stored_encodings_list:
            if stored_enc is not None and face_system.compare_faces(stored_enc, current_encoding):
                match_found = True
                break

        # Get bounding box for the current image to display feedback
        # Re-extract face encoding to get the bounding box from the *current* image
        _, bbox = face_system.extract_face_encoding(image) 
        image_with_bbox = image.copy() # Start with a copy of the original image
        if bbox: # If a face was detected, draw the box with voter's name
            image_with_bbox = face_system.draw_bounding_box(image_with_bbox, bbox, name=voter.name)

        # Encode image with bbox back to base64 for frontend display
        _, buffer = cv2.imencode('.jpg', image_with_bbox)
        encoded_image = base64.b64encode(buffer).decode('utf-8')
        image_data_with_bbox = f'data:image/jpeg;base64,{encoded_image}'

        if match_found:
            session['face_verified'] = True
            return jsonify({'success': True, 'message': 'Face verification successful', 'image_with_bbox': image_data_with_bbox})
        else:
            return jsonify({'success': False, 'message': 'Face verification failed. Please try again.', 'image_with_bbox': image_data_with_bbox})
            
    except Exception as e:
        logging.error(f"Face verification error: {str(e)}")
        return jsonify({'success': False, 'message': f'Verification error occurred: {str(e)}'})

@bp.route('/cast_vote', methods=['POST'])
def cast_vote():
    if 'voter_id' not in session or not session.get('face_verified'):
        flash('Face verification required!', 'error')
        return redirect(url_for('main.voter_panel'))
    
    try:
        voter = Voter.query.get(session['voter_id'])
        candidate_id = request.form.get('candidate_id')
        
        if not voter or not candidate_id:
            flash('Invalid vote data!', 'error')
            return redirect(url_for('main.voter_panel'))
        
        if voter.has_voted:
            flash('You have already voted!', 'error')
            return redirect(url_for('main.voter_panel'))
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            flash('Invalid candidate!', 'error')
            return redirect(url_for('main.voter_panel'))
        
        # Get the most recent election
        election = Election.query.order_by(Election.created_at.desc()).first()
        if not election:
            flash('No election configured. Please contact an administrator.', 'error')
            return redirect(url_for('main.voter_panel'))
        
        tz = pytz.timezone(election.timezone)
        now_aware = datetime.now(tz)
        
        election_start_time_aware = pytz.utc.localize(election.start_time).astimezone(tz)
        election_end_time_aware = pytz.utc.localize(election.end_time).astimezone(tz)

        if not (election_start_time_aware <= now_aware <= election_end_time_aware):
            flash('Voting is currently not open. Please check election times.', 'error')
            return redirect(url_for('main.voter_panel'))

        # Record the vote
        new_vote = Vote(voter_id=voter.id, candidate_id=candidate.id, election_id=election.id)
        db.session.add(new_vote)
        
        # Update candidate vote count
        candidate.votes += 1
        
        # Mark voter as voted
        voter.has_voted = True
        
        db.session.commit()

        # --- Blockchain Integration ---
        # Import Block and BlockchainRecord here to avoid circular imports
        from blockchain_utils import Block
        from models import BlockchainRecord

        # Access the blockchain instance from current_app
        blockchain = current_app.blockchain
        if not blockchain:
            current_app.logger.error("Blockchain not initialized in app.py!")
            flash('Blockchain system error. Please contact admin.', 'error')
            return redirect(url_for('main.voter_panel'))

        # Prepare vote data for the block
        vote_data = {
            "voter_id": voter.id,
            "candidate_id": candidate.id,
            "election_id": election.id,
            "timestamp": datetime.utcnow().isoformat() # Use UTC for blockchain consistency
        }

        # Create a new block
        # Ensure the blockchain has at least a genesis block
        if not blockchain.chain:
            blockchain.create_genesis_block()

        new_block = Block(len(blockchain.chain), datetime.utcnow(), vote_data, blockchain.last_block.hash)
        blockchain.add_block(new_block)

        # Save the blockchain record to the database
        blockchain_record = BlockchainRecord(
            block_hash=new_block.hash,
            previous_hash=new_block.previous_hash,
            election_id=election.id,
            vote_data=json.dumps(vote_data), # Store raw vote data as JSON string
            timestamp=new_block.timestamp, # Use block's timestamp
            nonce=new_block.nonce
        )
        db.session.add(blockchain_record)
        
        # Link the vote to the blockchain record
        new_vote.blockchain_hash = new_block.hash

        db.session.commit() # Commit blockchain record and vote update
        current_app.logger.info(f"Vote cast and recorded on blockchain: Block Hash {new_block.hash}")
        # --- End Blockchain Integration ---
        
        # Clear face verification session
        session.pop('face_verified', None)
        
        flash('Vote cast successfully!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logging.error(f"Vote casting error: {str(e)}")
        flash(f'Error casting vote: {str(e)}!', 'error')
        db.session.rollback()
        return redirect(url_for('main.voter_panel'))

@bp.route('/results')
def results():
    candidates = Candidate.query.order_by(Candidate.votes.desc()).all()
    total_votes = sum(candidate.votes for candidate in candidates)
    
    # Fetch all blockchain records
    blockchain_records = BlockchainRecord.query.order_by(BlockchainRecord.timestamp.asc()).all()

    return render_template('results.html', 
                           candidates=candidates, 
                           total_votes=total_votes,
                           blockchain_records=blockchain_records)

@bp.route('/api/results')
def api_results():
    """API endpoint for chart data"""
    candidates = Candidate.query.all()
    
    data = {
        'labels': [candidate.name for candidate in candidates],
        'votes': [candidate.votes for candidate in candidates],
        'colors': ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899']
    }
    
    return jsonify(data)
