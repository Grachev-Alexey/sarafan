from app import db
from sqlalchemy.orm import relationship, backref
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

salon_categories = db.Table('salon_categories',
    db.Column('salon_id', db.String(255), db.ForeignKey('partner_info.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)

class ClientSalonStatus(db.Model):
    __tablename__ = 'client_salon_status'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients_data.id'), nullable=False)
    salon_id = db.Column(db.String(255), db.ForeignKey('partner_info.id'), nullable=False)
    status = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('client_id', 'salon_id', name='unique_client_salon_status'),
    )

    def __repr__(self):
        return f"<ClientSalonStatus(client_id='{self.client_id}', salon_id='{self.salon_id}', status='{self.status}')>"

class ClientsData(db.Model):
    __tablename__ = 'clients_data'

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(255), nullable=False, unique=True)
    initial_salon_name = db.Column(db.String(255), nullable=False)
    initial_salon_id = db.Column(db.String(255), nullable=False)
    claimed_salon_name = db.Column(db.String(255), nullable=True)
    claimed_salon_id = db.Column(db.String(255), nullable=True)
    chosen_salon_name = db.Column(db.String(255), nullable=True)
    chosen_salon_id = db.Column(db.String(255), nullable=True)
    client_name = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(255), nullable=True)
    discount_claimed = db.Column(db.Boolean, default=False)
    attempts_left = db.Column(db.Integer, default=1)
    salon_statuses = relationship('ClientSalonStatus', backref='client', lazy='dynamic')

    def __repr__(self):
        return f"<ClientsData(chat_id='{self.chat_id}', initial_salon_name='{self.initial_salon_name}', claimed_salon_name='{self.claimed_salon_name}')>"

class PartnerInfo(db.Model):
    __tablename__ = 'partner_info'

    id = db.Column(db.String(255), primary_key=True)
    partner_type = db.Column(db.String(255), nullable=False)
    categories = db.relationship('Category', secondary=salon_categories, backref=db.backref('partners', lazy=True))
    name = db.Column(db.String(255), nullable=False)
    discount = db.Column(db.Text, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    city = db.relationship('City', backref=db.backref('partners', lazy=True))
    contacts = db.Column(db.String(255), nullable=False)
    clients_brought = db.Column(db.Integer, default=0)
    clients_received = db.Column(db.Integer, default=0)
    priority = db.Column(db.Boolean, default=False)
    linked_partner_id = db.Column(db.String(255), nullable=True)
    message_partner_name = db.Column(db.String(255), nullable=True)
    owner = db.Column(db.String(255), nullable=True)
    client_statuses = relationship('ClientSalonStatus', backref='salon', lazy='dynamic')
    invited_by = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=True)
    partners = relationship(
        'Partner',
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys='Partner.salon_id',
        single_parent=True
    )

    def __repr__(self):
        return f"<PartnerInfo(id='{self.id}', name='{self.name}', categories='{self.categories}', city='{self.city}', linked_partner_id='{self.linked_partner_id}', message_partner_name='{self.message_partner_name}')>"


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)

    def __str__(self):
        return self.name
        
class MessageTemplate(db.Model):
    """Модель для хранения шаблонов сообщений."""
    __tablename__ = 'message_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    template = db.Column(db.Text, nullable=False)

    def __str__(self):
        return self.name
        
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)    
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Partner(db.Model):
    __tablename__ = 'partners'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    salon_id = db.Column(db.String(255), db.ForeignKey('partner_info.id'), unique=True, nullable=False)
    referral_link = db.Column(db.String(255), unique=True, nullable=False)
    clients_brought = db.Column(db.Integer, default=0)
    clients_received = db.Column(db.Integer, default=0)
    partners_invited = db.Column(db.Integer, default=0)
    unique_code = db.Column(db.String(255), nullable=True)
    telegram_chat_id = db.Column(db.Integer, nullable=True)
    user = relationship('User', backref='partner', uselist=False)
    invited_partners = relationship("Partner",
                                   secondary="partner_invitations",
                                   primaryjoin="Partner.id==PartnerInvitation.inviting_partner_id",
                                   secondaryjoin="Partner.id==PartnerInvitation.invited_partner_id",
                                   backref=backref("invited_by", lazy="dynamic"),
                                   lazy="dynamic")
    salon = relationship('PartnerInfo', foreign_keys='Partner.salon_id', uselist=False, overlaps="partners")                             
        

    def __repr__(self):
        return f"<Partner(id='{self.id}', salon_id='{self.salon_id}')>"


class PartnerInvitation(db.Model):
    __tablename__ = 'partner_invitations'
    inviting_partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), primary_key=True)
    invited_partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), primary_key=True)
    
class DiscountWeightSettings(db.Model):
    __tablename__ = 'discount_weight_settings'

    id = db.Column(db.Integer, primary_key=True)
    ratio_40_80_weight = db.Column(db.Integer, default=3)
    ratio_30_40_weight = db.Column(db.Integer, default=2)
    ratio_below_30_weight = db.Column(db.Integer, default=1)
    partners_invited_weight = db.Column(db.Integer, default=1)

class City(db.Model):
    __tablename__ = 'city'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)

    def __str__(self):
        return self.name    