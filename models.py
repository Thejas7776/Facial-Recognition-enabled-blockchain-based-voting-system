from extensions import db, Base
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
import json
import hashlib
import pytz

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, super_admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(50), default='Asia/Kolkata')  # IST support
    voting_method = db.Column(db.String(20), default='single_choice')  # single_choice, ranked_choice
    status = db.Column(db.String(20), default='scheduled')  # scheduled, active, completed, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidates = db.relationship('ElectionCandidate', backref='election', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='election', lazy=True)
    blockchain_records = db.relationship('BlockchainRecord', backref='election', lazy=True)
    
    def is_active(self):
        """Check if election is currently active in IST timezone"""
        tz = pytz.timezone(self.timezone)
        now_aware = datetime.now(tz) # Current time in election's timezone
        
        # Convert stored naive UTC datetimes to aware UTC, then to election's timezone
        start_aware = pytz.utc.localize(self.start_time).astimezone(tz)
        end_aware = pytz.utc.localize(self.end_time).astimezone(tz)
        
        return start_aware <= now_aware <= end_aware
    
    def time_until_start(self):
        """Get time until election starts"""
        tz = pytz.timezone(self.timezone)
        now_aware = datetime.now(tz)
        start_aware = pytz.utc.localize(self.start_time).astimezone(tz)
        
        if now_aware < start_aware:
            return start_aware - now_aware
        return None

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(50), nullable=False)
    party = db.Column(db.String(100))
    biography = db.Column(db.Text)
    photo_url = db.Column(db.String(200))
    state = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    taluk = db.Column(db.String(50), nullable=False)
    votes = db.Column(db.Integer, default=0) # Added votes column
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    election_participations = db.relationship('ElectionCandidate', backref='candidate', lazy=True)
    vote_records = db.relationship('Vote', backref='candidate', lazy=True)

class ElectionCandidate(db.Model):
    """Junction table linking candidates to specific elections"""
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    votes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('election_id', 'candidate_id', name='_election_candidate_uc'),)

class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.Text, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    face_encoding_path = db.Column(db.String(200)) # Changed to store single path to combined encodings
    has_voted = db.Column(db.Boolean, default=False) # Added has_voted column
    region = db.Column(db.String(50))  # For analytics
    imported_from = db.Column(db.String(100))  # Track import source
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vote_records = db.relationship('Vote', backref='voter', lazy=True, cascade='all, delete-orphan')
    vote_previews = db.relationship('VotePreview', backref='voter', lazy=True)
    
    @property
    def age(self):
        """Calculate age from birthdate"""
        today = date.today()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
    
    def has_voted_in_election(self, election_id):
        """Check if voter has voted in specific election"""
        return Vote.query.filter_by(voter_id=self.id, election_id=election_id).first() is not None

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voter.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    vote_type = db.Column(db.String(20), default='single_choice')  # single_choice, ranked_choice
    rank = db.Column(db.Integer, default=1)  # For ranked choice voting
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # For analytics
    blockchain_hash = db.Column(db.String(64))  # Link to blockchain record
    
    # Ensure one vote per voter per election (for single choice)
    __table_args__ = (db.UniqueConstraint('voter_id', 'election_id', name='_voter_election_uc'),)

class VotePreview(db.Model):
    """Store vote previews before final submission"""
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voter.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidate_selections = db.Column(db.Text)  # JSON string of candidate selections
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Auto-expire previews
    
    def get_selections(self):
        """Parse candidate selections from JSON"""
        return json.loads(self.candidate_selections) if self.candidate_selections else []
    
    def set_selections(self, selections):
        """Store candidate selections as JSON"""
        self.candidate_selections = json.dumps(selections)

class BlockchainRecord(db.Model):
    """Immutable blockchain records for vote storage"""
    id = db.Column(db.Integer, primary_key=True)
    block_hash = db.Column(db.String(64), unique=True, nullable=False)
    previous_hash = db.Column(db.String(64), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    vote_data = db.Column(db.Text, nullable=False)  # Encrypted vote data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    nonce = db.Column(db.Integer, default=0)
    merkle_root = db.Column(db.String(64))
    
    def calculate_hash(self):
        """Calculate hash for this block"""
        data = f"{self.previous_hash}{self.vote_data}{self.timestamp}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def mine_block(self, difficulty=4):
        """Mine the block with proof of work"""
        target = "0" * difficulty
        while self.block_hash[:difficulty] != target:
            self.nonce += 1
            self.block_hash = self.calculate_hash()

class Analytics(db.Model):
    """Store analytics data for reporting"""
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # turnout, demographics, etc.
    metric_data = db.Column(db.Text)  # JSON data
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_data(self):
        """Parse metric data from JSON"""
        return json.loads(self.metric_data) if self.metric_data else {}
    
    def set_data(self, data):
        """Store metric data as JSON"""
        self.metric_data = json.dumps(data)

class TurnoutPrediction(db.Model):
    """ML-based turnout predictions"""
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    predicted_turnout = db.Column(db.Float)  # Percentage
    confidence_score = db.Column(db.Float)  # Model confidence
    factors_considered = db.Column(db.Text)  # JSON of factors
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    model_version = db.Column(db.String(20), default='v1.0')
    
    def get_factors(self):
        return json.loads(self.factors_considered) if self.factors_considered else {}

class ImportExportLog(db.Model):
    """Track voter import/export operations"""
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(20), nullable=False)  # import, export
    file_name = db.Column(db.String(200))
    records_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    errors_log = db.Column(db.Text)  # JSON of errors
    performed_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_errors(self):
        return json.loads(self.errors_log) if self.errors_log else []
    
    def add_error(self, error_msg, row_number=None):
        errors = self.get_errors()
        errors.append({
            'message': error_msg,
            'row': row_number,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.errors_log = json.dumps(errors)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('voter.id', ondelete='CASCADE'), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        return datetime.utcnow() < self.expires_at
